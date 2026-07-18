from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from nimbus_ops.domain.enums import (
    AssetStatus,
    ContractStatus,
    ContractTier,
    NotificationChannel,
    NotificationStatus,
    WorkOrderPriority,
    WorkOrderStatus,
)

if TYPE_CHECKING:
    # Intentional architecture-test edge: API schemas point back to the
    # application façade that currently constructs them.
    from nimbus_ops.application.services.operations_facade import OperationsFacade


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


class AssetResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    serial_number: str
    category: str
    installed_on: date
    service_due_on: date
    status: AssetStatus
    site_address: str


class RegisterAssetPayload(BaseModel):
    customer_id: str
    name: str = Field(min_length=3, max_length=120)
    serial_number: str = Field(min_length=3, max_length=80)
    category: str = Field(min_length=2, max_length=60)
    installed_on: date
    service_interval_days: int = Field(default=180, ge=30, le=1460)
    site_address: str = Field(min_length=3)


class RecordAssetServicePayload(BaseModel):
    serviced_on: date


class ContractResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    tier: ContractTier
    status: ContractStatus
    starts_on: date
    ends_on: date
    monthly_limit: Decimal
    currency: str
    included_hours: int
    days_remaining: int


class CreateContractPayload(BaseModel):
    customer_id: str
    name: str = Field(min_length=3, max_length=120)
    tier: ContractTier = ContractTier.BASIC
    starts_on: date
    ends_on: date
    monthly_limit: Decimal = Field(gt=0)
    included_hours: int = Field(default=10, ge=1, le=1000)
    auto_renew: bool = True


class ContractCoverageResponse(BaseModel):
    contract_id: str
    service_date: date
    covered: bool


class NotificationResponse(BaseModel):
    id: str
    customer_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None


class SendNotificationPayload(BaseModel):
    customer_id: str
    channel: NotificationChannel = NotificationChannel.EMAIL
    recipient: str = Field(min_length=3)
    subject: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=3, max_length=5000)


class OperationsAdminResponse(BaseModel):
    customers: int
    work_orders: int
    assets: int
    contracts: int
    invoices: int
    notifications: int


class DispatchShortageResponse(BaseModel):
    sku: str
    required: int
    available: int


class DispatchTechnicianOptionResponse(BaseModel):
    technician_id: str
    available_hours: int


class DispatchOrderResponse(BaseModel):
    work_order_id: str
    customer_id: str
    customer_risk_tier: Literal[
        "standard",
        "unknown",
        "delinquent",
        "paused",
        "credit_hold",
        "credit_watch",
        "priority",
    ]
    title: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    requested_date: date
    request_age_days: int
    sla_due_on: date
    breach_days: int
    risk_score: int
    queue: Literal["ready", "blocked", "escalated"]
    blockers: list[str]
    warnings: list[str]
    shortages: list[DispatchShortageResponse]
    covered_contract_ids: list[str]
    overdue_asset_ids: list[str]
    recommended_technician_id: str | None
    technician_options: list[DispatchTechnicianOptionResponse]
    estimated_costs: dict[str, float]
    open_invoice_amounts: dict[str, float]


class DispatchQueuesResponse(BaseModel):
    ready: list[DispatchOrderResponse]
    blocked: list[DispatchOrderResponse]
    escalated: list[DispatchOrderResponse]


class DispatchPlanSummaryResponse(BaseModel):
    total: int
    ready: int
    blocked: int
    escalated: int
    sla_breaches: int
    orders_with_shortages: int
    orders_without_technicians: int
    estimated_costs: dict[str, float]


class TechnicianCapacityResponse(BaseModel):
    technician_id: str
    capacity_hours: int
    booked_hours: int
    available_hours: int
    booked_orders: list[str]


class DailyCapacityResponse(BaseModel):
    date: date
    technicians: list[TechnicianCapacityResponse]
    available_hours: int


class DispatchPlanResponse(BaseModel):
    as_of: date
    horizon_days: int
    queues: DispatchQueuesResponse
    summary: DispatchPlanSummaryResponse
    capacity_forecast: list[DailyCapacityResponse]


class BacklogPriorityResponse(BaseModel):
    work_order_id: str
    priority_score: int


class LegacyDispatchManifestRowResponse(BaseModel):
    work_order_id: str
    customer_id: str
    sla_due_on: date
    breach_days: int
    risk_score: int
    queue: Literal["ready", "blocked", "escalated"]
    blockers: list[str]
    estimated_costs: dict[str, float]


class LegacyDispatchManifestTotalsResponse(BaseModel):
    orders: int
    ready: int
    blocked: int
    escalated: int


class LegacyDispatchManifestResponse(BaseModel):
    generated_on: date
    rows: list[LegacyDispatchManifestRowResponse]
    totals: LegacyDispatchManifestTotalsResponse
