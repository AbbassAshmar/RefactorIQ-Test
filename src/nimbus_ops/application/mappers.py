from __future__ import annotations

from nimbus_ops.application.dto import InventoryHealth, InvoiceSummary, WorkOrderSummary
from nimbus_ops.domain.entities import InventoryItem, Invoice, WorkOrder


def to_work_order_summary(work_order: WorkOrder) -> WorkOrderSummary:
    return WorkOrderSummary(
        id=work_order.id,
        customer_id=work_order.customer_id,
        title=work_order.title,
        priority=work_order.priority,
        status=work_order.status,
        requested_date=work_order.requested_date,
        scheduled_date=work_order.scheduled_date,
        assigned_technician_id=work_order.assigned_technician_id,
    )


def to_invoice_summary(invoice: Invoice) -> InvoiceSummary:
    total = invoice.subtotal()
    return InvoiceSummary(
        id=invoice.id,
        customer_id=invoice.customer_id,
        work_order_id=invoice.work_order_id,
        status=invoice.status.value,
        total=total.amount,
        currency=total.currency,
    )


def to_inventory_health(item: InventoryItem) -> InventoryHealth:
    return InventoryHealth(
        sku=item.sku,
        name=item.name,
        quantity_on_hand=item.quantity_on_hand,
        reorder_point=item.reorder_point,
        should_reorder=item.should_reorder(),
    )
