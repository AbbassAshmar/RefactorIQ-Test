from __future__ import annotations

from datetime import timedelta
from typing import Any

from nimbus_ops.application.services.operational_control_tower import ControlTowerSnapshot
from nimbus_ops.domain.enums import (
    ContractStatus,
    CustomerStatus,
    InvoiceStatus,
    WorkOrderPriority,
    WorkOrderStatus,
)


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


def _collect_due_records(snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
    return [
        {
            "kind": "asset",
            "id": asset.id,
            "customer_id": _normalize_identifier(asset.customer_id),
            "due_on": asset.service_due_on().isoformat(),
        }
        for asset in snapshot.assets
        if asset.needs_service(snapshot.as_of)
    ] + [
        {
            "kind": "contract",
            "id": contract.id,
            "customer_id": _normalize_identifier(contract.customer_id),
            "due_on": contract.ends_on.isoformat(),
        }
        for contract in snapshot.contracts
        if contract.status == ContractStatus.ACTIVE
        and 0 <= (contract.ends_on - snapshot.as_of).days <= 45
    ]


class LegacyOperationsExporter:
    """A second, independently evolved reporting path with overlapping logic."""

    def export_customer_rows(self, snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
        customer_rows = []
        for customer in snapshot.customers:
            work_orders = []
            for order in snapshot.work_orders:
                if order.customer_id != customer.id:
                    continue
                line_items = []
                for part in order.required_parts:
                    stock = next(
                        (item for item in snapshot.inventory if item.sku == part.sku),
                        None,
                    )
                    line_items.append(
                        {
                            "sku": part.sku,
                            "quantity": part.quantity,
                            "available": stock.quantity_on_hand if stock else 0,
                            "short": not stock or stock.quantity_on_hand < part.quantity,
                        }
                    )
                work_orders.append(
                    {
                        "id": order.id,
                        "status": order.status.value,
                        "priority": order.priority.value,
                        "parts": line_items,
                    }
                )

            invoice_total = 0.0
            for invoice in snapshot.invoices:
                if invoice.customer_id == customer.id and invoice.status == InvoiceStatus.ISSUED:
                    invoice_total += float(invoice.subtotal().amount)

            customer_rows.append(
                {
                    "customer_key": _normalize_identifier(customer.name),
                    "customer_id": customer.id,
                    "work_orders": work_orders,
                    "asset_count": sum(1 for asset in snapshot.assets if asset.customer_id == customer.id),
                    "active_contracts": sum(
                        1
                        for contract in snapshot.contracts
                        if contract.customer_id == customer.id and contract.status == ContractStatus.ACTIVE
                    ),
                    "open_invoice_total": round(invoice_total, 2),
                    "notification_count": sum(
                        1
                        for notification in snapshot.notifications
                        if notification.customer_id == customer.id
                    ),
                }
            )
        return sorted(customer_rows, key=lambda row: row["customer_key"])

    def export_exception_rows(self, snapshot: ControlTowerSnapshot) -> list[dict[str, Any]]:
        exceptions = []
        for row in self.export_customer_rows(snapshot):
            for order in row["work_orders"]:
                if order["status"] in {WorkOrderStatus.DRAFT.value, WorkOrderStatus.READY.value}:
                    shortages = [part for part in order["parts"] if part["short"]]
                    if shortages:
                        exceptions.append(
                            {
                                "customer_id": row["customer_id"],
                                "work_order_id": order["id"],
                                "shortages": shortages,
                            }
                        )
        return exceptions

    def export_dispatch_manifest(self, snapshot: ControlTowerSnapshot) -> dict[str, Any]:
        """Produce the fixed-shape dispatch payload consumed by a legacy partner."""
        customers_by_id = {customer.id: customer for customer in snapshot.customers}
        rows = []
        for order in snapshot.work_orders:
            if order.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                continue

            sla_due_on = order.requested_date + timedelta(
                days=_dispatch_sla_target_days(order.priority)
            )
            breach_days = max((snapshot.as_of - sla_due_on).days, 0)
            blockers = []
            part_costs: list[tuple[str, float]] = []
            customer = customers_by_id.get(order.customer_id)
            if customer is None:
                blockers.append("customer_missing")
            elif customer.status == CustomerStatus.DELINQUENT:
                blockers.append("customer_delinquent")
            elif customer.status == CustomerStatus.PAUSED:
                blockers.append("customer_paused")

            for part in order.required_parts:
                stock = next(
                    (item for item in snapshot.inventory if item.sku == part.sku),
                    None,
                )
                if stock is None:
                    blockers.append("part_shortage")
                if stock is not None:
                    part_costs.append(
                        (
                            stock.unit_cost.currency,
                            float(stock.unit_cost.amount) * part.quantity,
                        )
                    )

            priority_points = {
                WorkOrderPriority.EMERGENCY: 45,
                WorkOrderPriority.HIGH: 30,
                WorkOrderPriority.NORMAL: 15,
                WorkOrderPriority.LOW: 5,
            }[order.priority]
            risk_score = min(
                priority_points
                + min(breach_days * 4, 35)
                + min(len(blockers) * 15, 30),
                100,
            )
            queue_name = _dispatch_queue_name(
                order.priority,
                breach_days,
                risk_score,
                blockers,
            )
            rows.append(
                {
                    "work_order_id": order.id,
                    "customer_id": _normalize_identifier(order.customer_id),
                    "sla_due_on": sla_due_on.isoformat(),
                    "breach_days": breach_days,
                    "risk_score": risk_score,
                    "queue": queue_name,
                    "blockers": sorted(set(blockers)),
                    "estimated_costs": _dispatch_estimated_costs(
                        order.labor_rate.currency,
                        float(order.estimated_labor_total().amount),
                        part_costs,
                    ),
                }
            )

        rows.sort(
            key=lambda row: (
                {"escalated": 0, "blocked": 1, "ready": 2}[str(row["queue"])],
                -int(row["risk_score"]),
                str(row["work_order_id"]),
            )
        )
        return {
            "generated_on": snapshot.as_of.isoformat(),
            "rows": rows,
            "totals": {
                "orders": len(rows),
                "ready": sum(1 for row in rows if row["queue"] == "ready"),
                "blocked": sum(1 for row in rows if row["queue"] == "blocked"),
                "escalated": sum(1 for row in rows if row["queue"] == "escalated"),
            },
        }

    def export(self, snapshot: ControlTowerSnapshot) -> dict[str, Any]:
        rows = self.export_customer_rows(snapshot)
        due_records = _collect_due_records(snapshot)
        return {
            "generated_on": snapshot.as_of.isoformat(),
            "customers": rows,
            "due_records": due_records,
            "exceptions": self.export_exception_rows(snapshot),
            "totals": {
                "customers": len(rows),
                "orders": sum(len(row["work_orders"]) for row in rows),
                "due_records": len(due_records),
            },
        }
