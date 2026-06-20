from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from nimbus_ops.domain.enums import WorkOrderPriority, WorkOrderStatus
from nimbus_ops.domain.value_objects import Address


@dataclass(frozen=True)
class RequiredPartDTO:
    sku: str
    quantity: int


@dataclass(frozen=True)
class CreateWorkOrderCommand:
    customer_id: str
    title: str
    description: str
    priority: WorkOrderPriority
    requested_date: date
    site_address: Address
    required_parts: list[RequiredPartDTO]
    required_skills: set[str]
    estimated_hours: int


@dataclass(frozen=True)
class WorkOrderSummary:
    id: str
    customer_id: str
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    requested_date: date
    scheduled_date: date | None
    assigned_technician_id: str | None


@dataclass(frozen=True)
class ScheduleWorkOrderCommand:
    work_order_id: str
    scheduled_date: date
    unavailable_technician_ids: set[str]


@dataclass(frozen=True)
class CompleteWorkOrderCommand:
    work_order_id: str
    completed_at: datetime
    note: str | None


@dataclass(frozen=True)
class InvoiceSummary:
    id: str
    customer_id: str
    work_order_id: str
    status: str
    total: Decimal
    currency: str


@dataclass(frozen=True)
class InventoryHealth:
    sku: str
    name: str
    quantity_on_hand: int
    reorder_point: int
    should_reorder: bool
