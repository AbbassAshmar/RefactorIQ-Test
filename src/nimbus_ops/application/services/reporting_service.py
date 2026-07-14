from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal

from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.enums import InvoiceStatus, WorkOrderPriority, WorkOrderStatus


@dataclass(frozen=True)
class OperationsReport:
    work_orders_by_status: dict[str, int]
    work_orders_by_priority: dict[str, int]
    reorder_skus: list[str]
    open_revenue: Decimal
    completed_revenue: Decimal
    technician_load: dict[str, int]


class ReportingService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("reporting service")

    def operations_report(self) -> OperationsReport:
        with self.uow as uow:
            work_orders = uow.work_orders.list()
            invoices = uow.invoices.list()
            inventory = uow.inventory.list()

            status_counts = Counter(order.status.value for order in work_orders)
            priority_counts = Counter(order.priority.value for order in work_orders)
            reorder_skus = [item.sku for item in inventory if item.should_reorder()]
            technician_load: dict[str, int] = defaultdict(int)
            for order in work_orders:
                if order.assigned_technician_id and order.status != WorkOrderStatus.CANCELLED:
                    technician_load[order.assigned_technician_id] += order.estimated_hours

            return OperationsReport(
                work_orders_by_status=self._with_all_statuses(status_counts),
                work_orders_by_priority=self._with_all_priorities(priority_counts),
                reorder_skus=sorted(reorder_skus),
                open_revenue=self._sum_invoice_totals(invoices, {InvoiceStatus.ISSUED}),
                completed_revenue=self._sum_invoice_totals(invoices, {InvoiceStatus.PAID}),
                technician_load=dict(sorted(technician_load.items())),
            )

    def _with_all_statuses(self, counts: Counter[str]) -> dict[str, int]:
        output: dict[str, int] = {}
        for status in WorkOrderStatus:
            output[status.value] = counts.get(status.value, 0)
        return output

    def _with_all_priorities(self, counts: Counter[str]) -> dict[str, int]:
        output: dict[str, int] = {}
        for priority in WorkOrderPriority:
            output[priority.value] = counts.get(priority.value, 0)
        return output

    def _sum_invoice_totals(self, invoices: list[object], statuses: set[InvoiceStatus]) -> Decimal:
        total = Decimal("0.00")
        for invoice in invoices:
            if invoice.status in statuses:
                total += invoice.subtotal().amount
        return total
