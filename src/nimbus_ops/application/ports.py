from __future__ import annotations

from datetime import date
from typing import Protocol

from nimbus_ops.domain.entities import Customer, InventoryItem, Invoice, Technician, WorkOrder
from nimbus_ops.domain.events import DomainEvent


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


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


class UnitOfWork(Protocol):
    customers: CustomerRepository
    work_orders: WorkOrderRepository
    inventory: InventoryRepository
    technicians: TechnicianRepository
    invoices: InvoiceRepository
    events: EventPublisher

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def commit(self) -> None: ...
