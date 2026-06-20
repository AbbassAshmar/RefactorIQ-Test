from __future__ import annotations

from datetime import date, timedelta

from nimbus_ops.application.dto import InvoiceSummary
from nimbus_ops.application.mappers import to_invoice_summary
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.domain.entities import Invoice, InvoiceLine, new_id
from nimbus_ops.domain.enums import InvoiceStatus, WorkOrderStatus
from nimbus_ops.domain.events import invoice_issued
from nimbus_ops.domain.exceptions import EntityNotFoundError
from nimbus_ops.domain.value_objects import Money


class BillingService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create_invoice_from_work_order(self, work_order_id: str, issued_on: date) -> InvoiceSummary:
        with self.uow as uow:
            work_order = uow.work_orders.get(work_order_id)
            if work_order is None:
                raise EntityNotFoundError("WorkOrder", work_order_id)
            if work_order.status != WorkOrderStatus.COMPLETED:
                raise ValueError("Only completed work orders can be invoiced.")

            inventory = uow.inventory.get_many([part.sku for part in work_order.required_parts])
            lines = [
                InvoiceLine(
                    description=f"Labor for {work_order.title}",
                    quantity=work_order.estimated_hours,
                    unit_price=work_order.labor_rate,
                )
            ]
            for part in work_order.required_parts:
                item = inventory.get(part.sku)
                unit_price = item.unit_cost.multiply(1.35) if item else Money.from_float(0)
                lines.append(InvoiceLine(description=f"Part {part.sku}", quantity=part.quantity, unit_price=unit_price))

            invoice = Invoice(
                id=new_id("inv"),
                customer_id=work_order.customer_id,
                work_order_id=work_order.id,
                status=InvoiceStatus.DRAFT,
                issued_on=None,
                due_on=None,
                lines=lines,
            )
            invoice.issue(issued_on=issued_on, due_on=issued_on + timedelta(days=30))
            uow.invoices.save(invoice)
            total = invoice.subtotal()
            uow.events.publish(invoice_issued(invoice.id, invoice.customer_id, str(total.amount)))
            uow.commit()
            return to_invoice_summary(invoice)

    def list_invoices(self) -> list[InvoiceSummary]:
        with self.uow as uow:
            return [to_invoice_summary(invoice) for invoice in uow.invoices.list()]
