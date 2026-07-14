from __future__ import annotations

from datetime import date

from nimbus_ops.application.dto import (
    CompleteWorkOrderCommand,
    CreateWorkOrderCommand,
    ScheduleWorkOrderCommand,
)
from nimbus_ops.application.services.asset_service import AssetService
from nimbus_ops.application.services.billing_service import BillingService
from nimbus_ops.application.services.customer_service import CustomerService
from nimbus_ops.application.services.contract_service import ContractService
from nimbus_ops.application.services.inventory_service import InventoryService
from nimbus_ops.application.services.notification_service import NotificationService
from nimbus_ops.application.services.operational_control_tower import (
    ControlTowerSnapshot,
    OperationalControlTower,
)
from nimbus_ops.infrastructure.legacy_operations_exporter import LegacyOperationsExporter
from nimbus_ops.application.services.reporting_service import ReportingService
from nimbus_ops.application.services.work_order_service import WorkOrderService
from nimbus_ops.infrastructure.repositories import SQLiteUnitOfWork
from nimbus_ops.interfaces.api.schemas import (
    AssetResponse,
    ContractResponse,
    CustomerResponse,
    InventoryResponse,
    InvoiceResponse,
    NotificationResponse,
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
        self.asset_service = AssetService(uow)
        self.contract_service = ContractService(uow)
        self.inventory_service = InventoryService(uow)
        self.notification_service = NotificationService(uow)
        self.control_tower = OperationalControlTower()
        self.legacy_exporter = LegacyOperationsExporter()
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

    def asset_responses(self) -> list[AssetResponse]:
        return [
            AssetResponse(**asset.__dict__)
            for asset in self.asset_service.list_assets()
        ]

    def contract_responses(self) -> list[ContractResponse]:
        return [
            ContractResponse(**contract.__dict__)
            for contract in self.contract_service.list_contracts()
        ]

    def notification_responses(self) -> list[NotificationResponse]:
        return [
            NotificationResponse(**notification.__dict__)
            for notification in self.notification_service.list_notifications()
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

    def control_tower_snapshot(self) -> dict[str, object]:
        with self.uow as uow:
            snapshot = ControlTowerSnapshot(
                customers=uow.customers.list(),
                work_orders=uow.work_orders.list(),
                assets=uow.assets.list(),
                contracts=uow.contracts.list(),
                invoices=uow.invoices.list(),
                notifications=uow.notifications.list(),
                technicians=uow.technicians.list(),
                inventory=uow.inventory.list(),
                as_of=date.today(),
            )
            return self.control_tower.build_snapshot(snapshot)

    def legacy_operations_export(self) -> dict[str, object]:
        with self.uow as uow:
            snapshot = ControlTowerSnapshot(
                customers=uow.customers.list(),
                work_orders=uow.work_orders.list(),
                assets=uow.assets.list(),
                contracts=uow.contracts.list(),
                invoices=uow.invoices.list(),
                notifications=uow.notifications.list(),
                technicians=uow.technicians.list(),
                inventory=uow.inventory.list(),
                as_of=date.today(),
            )
            return self.legacy_exporter.export(snapshot)
