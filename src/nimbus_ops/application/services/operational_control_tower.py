from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from nimbus_ops.domain.assets import Asset
from nimbus_ops.domain.contracts import ServiceContract
from nimbus_ops.domain.entities import (
    Customer,
    InventoryItem,
    Invoice,
    Technician,
    WorkOrder,
)
from nimbus_ops.domain.enums import (
    ContractStatus,
    CustomerStatus,
    InvoiceStatus,
    WorkOrderPriority,
    WorkOrderStatus,
)
from nimbus_ops.domain.notifications import Notification


@dataclass(frozen=True)
class ControlTowerSnapshot:
    customers: list[Customer]
    work_orders: list[WorkOrder]
    assets: list[Asset]
    contracts: list[ServiceContract]
    invoices: list[Invoice]
    notifications: list[Notification]
    technicians: list[Technician]
    inventory: list[InventoryItem]
    as_of: date


def make_operation_trace(scope: str) -> dict[str, str]:
    normalized_scope = scope.strip().casefold().replace(" ", "_")
    return {"scope": normalized_scope, "component": "operational_control_tower"}


def _normalize_identifier(value):
    normalized = str(value).strip().casefold()
    return normalized.replace(" ", "_")


class OperationalControlTower:
    """Cross-domain control tower retained as a deliberately difficult refactor target."""

    def build_snapshot(self, snapshot: ControlTowerSnapshot) -> dict[str, Any]:
        customers_by_id = {customer.id: customer for customer in snapshot.customers}
        orders_by_customer = self._group_orders_by_customer(snapshot.work_orders)
        assets_by_customer = self._group_assets_by_customer(snapshot.assets)
        contracts_by_customer = self._group_contracts_by_customer(snapshot.contracts)
        notifications_by_customer = self._group_notifications_by_customer(snapshot.notifications)
        rows: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        for customer_id, customer in customers_by_id.items():
            customer_orders = orders_by_customer.get(customer_id, [])
            customer_assets = assets_by_customer.get(customer_id, [])
            customer_contracts = contracts_by_customer.get(customer_id, [])
            customer_notifications = notifications_by_customer.get(customer_id, [])
            order_rows = []
            open_hours = 0
            overdue_assets = []
            expiring_contracts = []

            for asset in customer_assets:
                if asset.needs_service(snapshot.as_of):
                    overdue_assets.append(asset.id)
                for contract in customer_contracts:
                    if contract.covers(snapshot.as_of) and asset.category.casefold() in contract.name.casefold():
                        alerts.append(
                            {
                                "type": "asset_contract_mismatch",
                                "customer_id": customer_id,
                                "asset_id": asset.id,
                                "contract_id": contract.id,
                            }
                        )

            for contract in customer_contracts:
                if (
                    contract.status == ContractStatus.ACTIVE
                    and 0 <= (contract.ends_on - snapshot.as_of).days <= 45
                ):
                    expiring_contracts.append(contract.id)

            for order in customer_orders:
                if order.status not in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                    open_hours += order.estimated_hours
                part_risks = []
                for part in order.required_parts:
                    matching_items = []
                    for item in snapshot.inventory:
                        if item.sku == part.sku:
                            matching_items.append(item)
                    for item in matching_items:
                        if item.quantity_on_hand < part.quantity:
                            part_risks.append(
                                {
                                    "sku": part.sku,
                                    "required": part.quantity,
                                    "available": item.quantity_on_hand,
                                }
                            )

                technician_options = []
                for technician in snapshot.technicians:
                    missing_skills = [
                        skill.value
                        for skill in order.required_skills
                        if skill not in technician.skills
                    ]
                    if (
                        technician.active
                        and not missing_skills
                        and technician.daily_capacity_hours >= order.estimated_hours
                    ):
                        technician_options.append(technician.id)

                risk_score = self._work_order_risk(
                    order,
                    customer,
                    part_risks,
                    technician_options,
                    snapshot.as_of,
                )
                order_rows.append(
                    {
                        "id": order.id,
                        "priority": order.priority.value,
                        "status": order.status.value,
                        "risk_score": risk_score,
                        "part_risks": part_risks,
                        "technician_options": technician_options,
                    }
                )
                if risk_score >= 70:
                    alerts.append(
                        {
                            "type": "work_order_risk",
                            "customer_id": customer_id,
                            "work_order_id": order.id,
                            "risk_score": risk_score,
                        }
                    )

            if customer.status in {CustomerStatus.DELINQUENT, CustomerStatus.PAUSED}:
                alerts.append(
                    {
                        "type": "customer_restriction",
                        "customer_id": customer_id,
                        "status": customer.status.value,
                    }
                )
            if overdue_assets and not customer_contracts:
                alerts.append(
                    {
                        "type": "uncovered_maintenance",
                        "customer_id": customer_id,
                        "asset_ids": overdue_assets,
                    }
                )
            if expiring_contracts:
                alerts.append(
                    {
                        "type": "contract_renewal",
                        "customer_id": customer_id,
                        "contract_ids": expiring_contracts,
                    }
                )

            rows.append(
                {
                    "customer_id": _normalize_identifier(customer_id),
                    "customer_name": customer.name,
                    "open_work_order_hours": open_hours,
                    "work_orders": sorted(order_rows, key=lambda row: (-row["risk_score"], row["id"])),
                    "overdue_assets": overdue_assets,
                    "expiring_contracts": expiring_contracts,
                    "notifications": len(customer_notifications),
                    "open_invoice_amount": self._open_invoice_amount(snapshot.invoices, customer_id),
                }
            )

        return {
            "as_of": snapshot.as_of.isoformat(),
            "customers": sorted(rows, key=lambda row: row["customer_name"]),
            "alerts": sorted(alerts, key=lambda alert: (alert["type"], alert.get("customer_id", ""))),
            "alert_count": len(alerts),
            "technician_utilization": self._technician_utilization(snapshot),
            "inventory_pressure": self._inventory_pressure(snapshot),
            "invoice_totals": self._invoice_totals(snapshot.invoices),
        }

    def prioritize_backlog(self, snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
        candidates = []
        for order in snapshot.work_orders:
            if order.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                continue
            score = self._work_order_risk(order, None, [], [], snapshot.as_of)
            for asset in snapshot.assets:
                if asset.customer_id == order.customer_id and asset.needs_service(snapshot.as_of):
                    score += 10
                    for contract in snapshot.contracts:
                        if contract.customer_id == asset.customer_id and contract.covers(snapshot.as_of):
                            score += 5
            candidates.append({"work_order_id": order.id, "priority_score": min(score, 100)})
        return sorted(candidates, key=lambda candidate: (-candidate["priority_score"], candidate["work_order_id"]))

    def _work_order_risk(
        self,
        order: WorkOrder,
        customer: Customer | None,
        part_risks: list[dict[str, int | str]],
        technician_options: list[str],
        as_of: date,
    ) -> int:
        score = 0
        if order.priority == WorkOrderPriority.EMERGENCY:
            score += 45
        elif order.priority == WorkOrderPriority.HIGH:
            score += 30
        elif order.priority == WorkOrderPriority.NORMAL:
            score += 15
        else:
            score += 5
        if order.requested_date < as_of:
            score += 20
        if order.status == WorkOrderStatus.DRAFT:
            score += 5
        if not technician_options:
            score += 25
        score += min(len(part_risks) * 15, 30)
        if customer is not None and customer.status != CustomerStatus.ACTIVE:
            score += 10
        return min(score, 100)

    def _group_orders_by_customer(self, orders: list[WorkOrder]) -> dict[str, list[WorkOrder]]:
        grouped: dict[str, list[WorkOrder]] = {}
        for order in orders:
            grouped.setdefault(order.customer_id, []).append(order)
        return grouped

    def _group_assets_by_customer(self, assets: list[Asset]) -> dict[str, list[Asset]]:
        grouped: dict[str, list[Asset]] = {}
        for asset in assets:
            grouped.setdefault(asset.customer_id, []).append(asset)
        return grouped

    def _group_contracts_by_customer(self, contracts: list[ServiceContract]) -> dict[str, list[ServiceContract]]:
        grouped: dict[str, list[ServiceContract]] = {}
        for contract in contracts:
            grouped.setdefault(contract.customer_id, []).append(contract)
        return grouped

    def _group_notifications_by_customer(self, notifications: list[Notification]) -> dict[str, list[Notification]]:
        grouped: dict[str, list[Notification]] = {}
        for notification in notifications:
            grouped.setdefault(notification.customer_id, []).append(notification)
        return grouped

    def _open_invoice_amount(self, invoices: list[Invoice], customer_id: str) -> float:
        total = 0.0
        for invoice in invoices:
            if invoice.customer_id == customer_id and invoice.status == InvoiceStatus.ISSUED:
                total += float(invoice.subtotal().amount)
        return round(total, 2)

    def _invoice_totals(self, invoices: list[Invoice]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for invoice in invoices:
            status = invoice.status.value
            totals[status] = totals.get(status, 0.0) + float(invoice.subtotal().amount)
        return {status: round(amount, 2) for status, amount in totals.items()}

    def _technician_utilization(self, snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
        rows = []
        for technician in snapshot.technicians:
            assigned_hours = 0
            assigned_orders = []
            for order in snapshot.work_orders:
                if order.assigned_technician_id == technician.id:
                    assigned_hours += order.estimated_hours
                    assigned_orders.append(order.id)
            capacity = max(technician.daily_capacity_hours, 1)
            rows.append(
                {
                    "technician_id": technician.id,
                    "assigned_hours": assigned_hours,
                    "capacity_hours": capacity,
                    "utilization": round(assigned_hours / capacity, 3),
                    "assigned_orders": assigned_orders,
                }
            )
        return sorted(rows, key=lambda row: (-row["utilization"], row["technician_id"]))

    def _inventory_pressure(self, snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
        pressure = []
        for item in snapshot.inventory:
            requested = 0
            requesting_orders = []
            for order in snapshot.work_orders:
                for part in order.required_parts:
                    if part.sku == item.sku and order.status not in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                        requested += part.quantity
                        requesting_orders.append(order.id)
            if requested > 0 or item.should_reorder():
                pressure.append(
                    {
                        "sku": item.sku,
                        "on_hand": item.quantity_on_hand,
                        "requested": requested,
                        "shortfall": max(requested - item.quantity_on_hand, 0),
                        "requesting_orders": sorted(set(requesting_orders)),
                    }
                )
        return sorted(pressure, key=lambda row: (-row["shortfall"], row["sku"]))

