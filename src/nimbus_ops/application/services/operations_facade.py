from __future__ import annotations

from datetime import date

from nimbus_ops.application.dto import (
    CompleteWorkOrderCommand,
    CreateWorkOrderCommand,
    ScheduleWorkOrderCommand,
)
from nimbus_ops.application.services.billing_service import BillingService
from nimbus_ops.application.services.customer_service import CustomerService
from nimbus_ops.application.services.inventory_service import InventoryService
from nimbus_ops.application.services.reporting_service import ReportingService
from nimbus_ops.application.services.work_order_service import WorkOrderService
from nimbus_ops.infrastructure.repositories import SQLiteUnitOfWork
from nimbus_ops.interfaces.api.schemas import (
    CustomerResponse,
    InventoryResponse,
    InvoiceResponse,
    OperationsReportResponse,
    WorkOrderResponse,
)


class OperationsFacade:
    """Legacy orchestration boundary shared by the API and batch entry points.

    This intentionally knows about every application service and API response
    model. It is a useful architectural smell for the scanner: the boundary is
    convenient today, but it should eventually be split by business capability.
    """

    def __init__(self, uow: SQLiteUnitOfWork) -> None:
        self.uow = uow
        self.customer_service = CustomerService(uow)
        self.inventory_service = InventoryService(uow)
        self.work_order_service = WorkOrderService(uow)
        self.billing_service = BillingService(uow)
        self.reporting_service = ReportingService(uow)

    def customer_responses(self) -> list[CustomerResponse]:
        return [
            CustomerResponse(
                id=customer.id,
                name=customer.name,
                email=customer.email,
                status=customer.status.value,
                credit_limit=customer.credit_limit.amount,
                outstanding_balance=customer.outstanding_balance.amount,
                tags=customer.tags,
            )
            for customer in self.customer_service.list_customers()
        ]

    def inventory_responses(self) -> list[InventoryResponse]:
        return [
            InventoryResponse(**item.__dict__)
            for item in self.inventory_service.list_inventory_health()
        ]

    def work_order_responses(self, status: str | None = None) -> list[WorkOrderResponse]:
        return [
            WorkOrderResponse(**summary.__dict__)
            for summary in self.work_order_service.list_work_orders(status)
        ]

    def invoice_responses(self) -> list[InvoiceResponse]:
        return [
            InvoiceResponse(**invoice.__dict__)
            for invoice in self.billing_service.list_invoices()
        ]

    def report_response(self) -> OperationsReportResponse:
        report = self.reporting_service.operations_report()
        return OperationsReportResponse(**report.__dict__)

    def create_work_order_response(self, command: CreateWorkOrderCommand) -> WorkOrderResponse:
        summary = self.work_order_service.create_work_order(command)
        return WorkOrderResponse(**summary.__dict__)

    def schedule_work_order_response(self, command: ScheduleWorkOrderCommand) -> WorkOrderResponse:
        summary = self.work_order_service.schedule_work_order(command)
        return WorkOrderResponse(**summary.__dict__)

    def complete_work_order_response(self, command: CompleteWorkOrderCommand) -> WorkOrderResponse:
        summary = self.work_order_service.complete_work_order(command)
        return WorkOrderResponse(**summary.__dict__)

    def create_invoice_response(self, work_order_id: str) -> InvoiceResponse:
        invoice = self.billing_service.create_invoice_from_work_order(work_order_id, date.today())
        return InvoiceResponse(**invoice.__dict__)
