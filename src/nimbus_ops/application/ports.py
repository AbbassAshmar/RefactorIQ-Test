from __future__ import annotations

from datetime import date
from typing import Protocol

from nimbus_ops.domain.assets import Asset
from nimbus_ops.domain.contracts import ServiceContract
from nimbus_ops.domain.entities import Customer, InventoryItem, Invoice, Technician, WorkOrder
from nimbus_ops.domain.events import DomainEvent
from nimbus_ops.domain.notifications import Notification


class CustomerRepository(Protocol):
    def get(self, customer_id: str) -> Customer | None: ...

    def list(self) -> list[Customer]: ...

    def save(self, customer: Customer) -> None: ...


class WorkOrderRepository(Protocol):
    def get(self, work_order_id: str) -> WorkOrder | None: ...

    def list(self, status: str | None = None) -> list[WorkOrder]: ...

    def list_for_date(self, scheduled_date: date) -> list[WorkOrder]: ...

    def save(self, work_order: WorkOrder) -> None: ...


class InventoryRepository(Protocol):
    def get_many(self, skus: list[str]) -> dict[str, InventoryItem]: ...

    def list(self) -> list[InventoryItem]: ...

    def save(self, item: InventoryItem) -> None: ...


class TechnicianRepository(Protocol):
    def list(self) -> list[Technician]: ...


class InvoiceRepository(Protocol):
    def get(self, invoice_id: str) -> Invoice | None: ...

    def list(self) -> list[Invoice]: ...

    def save(self, invoice: Invoice) -> None: ...


class AssetRepository(Protocol):
    def get(self, asset_id: str) -> Asset | None: ...

    def list(self, customer_id: str | None = None) -> list[Asset]: ...

    def save(self, asset: Asset) -> None: ...


class ContractRepository(Protocol):
    def get(self, contract_id: str) -> ServiceContract | None: ...

    def list(self, customer_id: str | None = None) -> list[ServiceContract]: ...

    def save(self, contract: ServiceContract) -> None: ...


class NotificationRepository(Protocol):
    def get(self, notification_id: str) -> Notification | None: ...

    def list(self, customer_id: str | None = None) -> list[Notification]: ...

    def save(self, notification: Notification) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


class UnitOfWork(Protocol):
    customers: CustomerRepository
    work_orders: WorkOrderRepository
    inventory: InventoryRepository
    technicians: TechnicianRepository
    invoices: InvoiceRepository
    assets: AssetRepository
    contracts: ContractRepository
    notifications: NotificationRepository
    events: EventPublisher

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def commit(self) -> None: ...
