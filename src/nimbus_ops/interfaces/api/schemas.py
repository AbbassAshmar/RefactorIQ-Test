from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from nimbus_ops.domain.enums import WorkOrderPriority, WorkOrderStatus


class AddressPayload(BaseModel):
    line1: str = Field(min_length=3)
    city: str = Field(min_length=2)
    country: str = Field(min_length=2, max_length=2)
    postal_code: str = Field(min_length=2)
    line2: str | None = None


class RequiredPartPayload(BaseModel):
    sku: str = Field(min_length=2)
    quantity: int = Field(gt=0)


class CreateWorkOrderPayload(BaseModel):
    customer_id: str
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=10)
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL
    requested_date: date
    site_address: AddressPayload
    required_skus: list[RequiredPartPayload] = Field(default_factory=list)
    required_skills: set[str] = Field(default_factory=set)
    estimated_hours: int = Field(default=2, ge=1, le=12)


class ScheduleWorkOrderPayload(BaseModel):
    scheduled_date: date
    unavailable_technician_ids: set[str] = Field(default_factory=set)


class CompleteWorkOrderPayload(BaseModel):
    completed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class WorkOrderResponse(BaseModel):
    id: str
    customer_id: str
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    requested_date: date
    scheduled_date: date | None
    assigned_technician_id: str | None


class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    credit_limit: Decimal
    outstanding_balance: Decimal
    tags: list[str]


class InventoryResponse(BaseModel):
    sku: str
    name: str
    quantity_on_hand: int
    reorder_point: int
    should_reorder: bool


class StockAdjustmentPayload(BaseModel):
    delta: int


class InvoiceResponse(BaseModel):
    id: str
    customer_id: str
    work_order_id: str
    status: str
    total: Decimal
    currency: str


class OperationsReportResponse(BaseModel):
    work_orders_by_status: dict[str, int]
    work_orders_by_priority: dict[str, int]
    reorder_skus: list[str]
    open_revenue: Decimal
    completed_revenue: Decimal
    technician_load: dict[str, int]
