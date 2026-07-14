from __future__ import annotations

from typing import Any

from nimbus_ops.application.services.operational_control_tower import ControlTowerSnapshot
from nimbus_ops.domain.enums import ContractStatus, InvoiceStatus, WorkOrderStatus


def _normalize_identifier(value):
    normalized = str(value).strip().casefold()
    return normalized.replace(" ", "_")


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
