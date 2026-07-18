from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
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


def _dispatch_sla_target_days(priority: WorkOrderPriority) -> int:
    if priority == WorkOrderPriority.EMERGENCY:
        return 0
    if priority == WorkOrderPriority.HIGH:
        return 1
    if priority == WorkOrderPriority.NORMAL:
        return 3
    return 7


def _dispatch_queue_name(
    priority: WorkOrderPriority,
    breach_days: int,
    risk_score: int,
    blockers: list[str],
) -> str:
    if (
        priority == WorkOrderPriority.EMERGENCY
        or breach_days > 0
        or risk_score >= 75
        or "customer_delinquent" in blockers
    ):
        return "escalated"
    if blockers:
        return "blocked"
    return "ready"


def _dispatch_estimated_costs(
    labor_currency: str,
    labor_amount: float,
    part_costs: list[tuple[str, float]],
) -> dict[str, float]:
    totals = {labor_currency: labor_amount}
    for currency, amount in part_costs:
        totals[currency] = totals.get(currency, 0.0) + amount
    return {currency: round(amount, 2) for currency, amount in totals.items()}


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
        customers_by_id = {customer.id: customer for customer in snapshot.customers}
        inventory_by_sku = {item.sku: item for item in snapshot.inventory}
        for order in snapshot.work_orders:
            if order.status not in {WorkOrderStatus.DRAFT, WorkOrderStatus.READY}:
                continue
            part_risks = []
            for part in order.required_parts:
                item = inventory_by_sku.get(part.sku)
                if item is None or not item.active:
                    part_risks.append(
                        {
                            "sku": part.sku,
                            "required": part.quantity,
                            "available": 0 if item is None else item.quantity_on_hand,
                        }
                    )
            technician_options = [
                technician.id
                for technician in snapshot.technicians
                if technician.can_handle(order.required_skills, order.estimated_hours)
            ]
            score = self._work_order_risk(
                order,
                customers_by_id.get(order.customer_id),
                part_risks,
                technician_options,
                snapshot.as_of,
            )
            for asset in snapshot.assets:
                if asset.customer_id == order.customer_id and asset.needs_service(snapshot.as_of):
                    score += 10
                    for contract in snapshot.contracts:
                        if contract.customer_id == asset.customer_id and contract.covers(snapshot.as_of):
                            score += 5
            candidates.append({"work_order_id": order.id, "priority_score": min(score, 100)})
        return sorted(candidates, key=lambda candidate: (-candidate["priority_score"], candidate["work_order_id"]))

    def build_dispatch_plan(
        self,
        snapshot: ControlTowerSnapshot,
        horizon_days: int = 14,
        include_scheduled: bool = False,
    ) -> dict[str, Any]:
        """Build the legacy cross-domain dispatch board used by operations.

        The implementation grew inside the control tower because the first
        version had to ship before the dispatch domain was separated. It now
        mixes SLA policy, customer credit checks, contract coverage, inventory,
        technician capacity, asset maintenance, and invoice exposure.
        """
        if horizon_days < 1 or horizon_days > 90:
            raise ValueError("Dispatch horizon must be between 1 and 90 days.")

        customers_by_id = {customer.id: customer for customer in snapshot.customers}
        inventory_by_sku = {item.sku: item for item in snapshot.inventory}
        contracts_by_customer = self._group_contracts_by_customer(snapshot.contracts)
        assets_by_customer = self._group_assets_by_customer(snapshot.assets)
        reserved_hours: dict[tuple[str, date], int] = {}
        horizon_end = snapshot.as_of + timedelta(days=horizon_days - 1)
        ready: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        escalated: list[dict[str, Any]] = []

        for scheduled_order in snapshot.work_orders:
            if (
                scheduled_order.assigned_technician_id
                and scheduled_order.scheduled_date
                and snapshot.as_of <= scheduled_order.scheduled_date <= horizon_end
                and scheduled_order.status
                in {WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS}
            ):
                technician_id = scheduled_order.assigned_technician_id
                capacity_key = (technician_id, scheduled_order.scheduled_date)
                reserved_hours[capacity_key] = (
                    reserved_hours.get(capacity_key, 0)
                    + scheduled_order.estimated_hours
                )

        priority_order = {
            WorkOrderPriority.EMERGENCY: 0,
            WorkOrderPriority.HIGH: 1,
            WorkOrderPriority.NORMAL: 2,
            WorkOrderPriority.LOW: 3,
        }
        dispatch_orders = sorted(
            snapshot.work_orders,
            key=lambda order: (
                order.requested_date
                + timedelta(days=_dispatch_sla_target_days(order.priority)),
                priority_order[order.priority],
                order.requested_date,
                order.id,
            ),
        )
        for order in dispatch_orders:
            if order.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                continue
            if order.status in {WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS}:
                if not include_scheduled:
                    continue
                if order.scheduled_date and order.scheduled_date > horizon_end:
                    continue

            customer = customers_by_id.get(order.customer_id)
            blockers: list[str] = []
            warnings: list[str] = []
            shortages: list[dict[str, int | str]] = []
            technician_options: list[dict[str, int | str]] = []
            covered_contract_ids: list[str] = []
            overdue_asset_ids: list[str] = []
            estimated_part_costs: list[tuple[str, float]] = []
            open_invoice_amounts: dict[str, float] = {}
            open_invoice_count = 0
            customer_risk_tier = "standard"

            age_days = max((snapshot.as_of - order.requested_date).days, 0)
            target_days = _dispatch_sla_target_days(order.priority)
            sla_due_on = order.requested_date + timedelta(days=target_days)
            breach_days = max((snapshot.as_of - sla_due_on).days, 0)

            if customer is None:
                customer_risk_tier = "unknown"
                blockers.append("customer_missing")
            elif customer.status == CustomerStatus.DELINQUENT:
                customer_risk_tier = "delinquent"
                blockers.append("customer_delinquent")
            elif customer.status == CustomerStatus.PAUSED:
                customer_risk_tier = "paused"
                blockers.append("customer_paused")
            elif customer.outstanding_balance.amount >= customer.credit_limit.amount:
                customer_risk_tier = "credit_hold"
                blockers.append("credit_limit_reached")
            elif (
                customer.outstanding_balance.amount
                >= customer.credit_limit.amount * Decimal("0.85")
            ):
                customer_risk_tier = "credit_watch"
                warnings.append("credit_limit_near")
            elif "priority" in customer.tags:
                customer_risk_tier = "priority"

            service_date = order.scheduled_date or snapshot.as_of
            dispatch_date = order.scheduled_date or snapshot.as_of
            for contract in contracts_by_customer.get(order.customer_id, []):
                if contract.covers(service_date):
                    covered_contract_ids.append(contract.id)
                elif (
                    contract.status == ContractStatus.ACTIVE
                    and contract.ends_on < service_date
                    and (service_date - contract.ends_on).days <= 30
                ):
                    warnings.append("contract_recently_expired")
            if not covered_contract_ids:
                warnings.append("contract_uncovered")

            for asset in assets_by_customer.get(order.customer_id, []):
                if asset.needs_service(snapshot.as_of):
                    overdue_asset_ids.append(asset.id)
                    if asset.category.casefold() in order.title.casefold():
                        warnings.append("related_asset_overdue")

            for part in order.required_parts:
                item = inventory_by_sku.get(part.sku)
                if item is None:
                    shortages.append(
                        {
                            "sku": part.sku,
                            "required": part.quantity,
                            "available": 0,
                        }
                    )
                    blockers.append("part_missing")
                else:
                    estimated_part_costs.append(
                        (
                            item.unit_cost.currency,
                            float(item.unit_cost.amount) * part.quantity,
                        )
                    )
                    if not item.active:
                        blockers.append("part_inactive")
                    if item.quantity_on_hand <= item.reorder_point:
                        warnings.append("stock_below_reorder_after_dispatch")

            for technician in snapshot.technicians:
                if not technician.active:
                    continue
                missing_skills = [
                    skill.value
                    for skill in order.required_skills
                    if skill not in technician.skills
                ]
                available_hours = max(
                    technician.daily_capacity_hours
                    - reserved_hours.get((technician.id, dispatch_date), 0),
                    0,
                )
                is_current_assignment = (
                    order.assigned_technician_id == technician.id
                    and order.scheduled_date == dispatch_date
                    and order.status
                    in {WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS}
                )
                if not missing_skills and (
                    is_current_assignment or available_hours >= order.estimated_hours
                ):
                    technician_options.append(
                        {
                            "technician_id": technician.id,
                            "available_hours": available_hours,
                        }
                    )
                elif not missing_skills and available_hours > 0:
                    warnings.append("technician_capacity_tight")
            technician_options.sort(
                key=lambda option: (
                    str(option["technician_id"]) != order.assigned_technician_id,
                    -int(option["available_hours"]),
                    str(option["technician_id"]),
                )
            )
            if not technician_options:
                blockers.append("technician_unavailable")

            for invoice in snapshot.invoices:
                if (
                    invoice.customer_id == order.customer_id
                    and invoice.status == InvoiceStatus.ISSUED
                ):
                    subtotal = invoice.subtotal()
                    open_invoice_count += 1
                    open_invoice_amounts[subtotal.currency] = (
                        open_invoice_amounts.get(subtotal.currency, 0.0)
                        + float(subtotal.amount)
                    )

            risk_score = self._work_order_risk(
                order,
                customer,
                shortages,
                [str(option["technician_id"]) for option in technician_options],
                snapshot.as_of,
            )
            if breach_days:
                risk_score += min(10 + breach_days * 3, 30)
            if not covered_contract_ids:
                risk_score += 5
            if overdue_asset_ids:
                risk_score += min(len(overdue_asset_ids) * 4, 12)
            if open_invoice_count:
                risk_score += min(open_invoice_count * 2, 8)
            risk_score = min(risk_score, 100)

            recommended_technician_id = (
                str(technician_options[0]["technician_id"])
                if technician_options
                else None
            )
            if (
                recommended_technician_id
                and not blockers
                and order.status
                not in {WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS}
            ):
                capacity_key = (recommended_technician_id, dispatch_date)
                reserved_hours[capacity_key] = (
                    reserved_hours.get(capacity_key, 0)
                    + order.estimated_hours
                )

            row = {
                "work_order_id": order.id,
                "customer_id": order.customer_id,
                "customer_risk_tier": customer_risk_tier,
                "title": order.title,
                "priority": order.priority.value,
                "status": order.status.value,
                "requested_date": order.requested_date.isoformat(),
                "request_age_days": age_days,
                "sla_due_on": sla_due_on.isoformat(),
                "breach_days": breach_days,
                "risk_score": risk_score,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
                "shortages": shortages,
                "covered_contract_ids": sorted(covered_contract_ids),
                "overdue_asset_ids": sorted(overdue_asset_ids),
                "recommended_technician_id": recommended_technician_id,
                "technician_options": technician_options,
                "estimated_costs": _dispatch_estimated_costs(
                    order.labor_rate.currency,
                    float(order.estimated_labor_total().amount),
                    estimated_part_costs,
                ),
                "open_invoice_amounts": {
                    currency: round(amount, 2)
                    for currency, amount in open_invoice_amounts.items()
                },
            }
            queue_name = _dispatch_queue_name(
                order.priority,
                breach_days,
                risk_score,
                blockers,
            )
            row["queue"] = queue_name
            if queue_name == "escalated":
                escalated.append(row)
            elif queue_name == "blocked":
                blocked.append(row)
            else:
                ready.append(row)

        sort_key = lambda row: (-int(row["risk_score"]), str(row["sla_due_on"]), str(row["work_order_id"]))
        ready.sort(key=sort_key)
        blocked.sort(key=sort_key)
        escalated.sort(key=sort_key)

        capacity_forecast: list[dict[str, Any]] = []
        for offset in range(horizon_days):
            service_day = snapshot.as_of + timedelta(days=offset)
            technician_rows = []
            for technician in snapshot.technicians:
                if not technician.active:
                    continue
                booked_hours = 0
                booked_orders = []
                for scheduled_order in snapshot.work_orders:
                    if (
                        scheduled_order.assigned_technician_id == technician.id
                        and scheduled_order.scheduled_date == service_day
                        and scheduled_order.status
                        not in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}
                    ):
                        booked_hours += scheduled_order.estimated_hours
                        booked_orders.append(scheduled_order.id)
                technician_rows.append(
                    {
                        "technician_id": technician.id,
                        "capacity_hours": technician.daily_capacity_hours,
                        "booked_hours": booked_hours,
                        "available_hours": max(
                            technician.daily_capacity_hours - booked_hours,
                            0,
                        ),
                        "booked_orders": sorted(booked_orders),
                    }
                )
            capacity_forecast.append(
                {
                    "date": service_day.isoformat(),
                    "technicians": technician_rows,
                    "available_hours": sum(
                        int(row["available_hours"]) for row in technician_rows
                    ),
                }
            )

        all_rows = ready + blocked + escalated
        estimated_costs: dict[str, float] = {}
        for row in all_rows:
            for currency, amount in row["estimated_costs"].items():
                estimated_costs[currency] = (
                    estimated_costs.get(currency, 0.0) + float(amount)
                )
        return {
            "as_of": snapshot.as_of.isoformat(),
            "horizon_days": horizon_days,
            "queues": {
                "ready": ready,
                "blocked": blocked,
                "escalated": escalated,
            },
            "summary": {
                "total": len(all_rows),
                "ready": len(ready),
                "blocked": len(blocked),
                "escalated": len(escalated),
                "sla_breaches": sum(1 for row in all_rows if int(row["breach_days"]) > 0),
                "orders_with_shortages": sum(1 for row in all_rows if row["shortages"]),
                "orders_without_technicians": sum(
                    1 for row in all_rows if row["recommended_technician_id"] is None
                ),
                "estimated_costs": {
                    currency: round(amount, 2)
                    for currency, amount in estimated_costs.items()
                },
            },
            "capacity_forecast": capacity_forecast,
        }

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
