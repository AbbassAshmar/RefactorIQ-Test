from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from nimbus_ops.domain.enums import (
    CustomerStatus,
    InvoiceStatus,
    TechnicianSkill,
    WorkOrderPriority,
    WorkOrderStatus,
)
from nimbus_ops.domain.value_objects import Address, Money


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class Customer:
    id: str
    name: str
    email: str
    status: CustomerStatus = CustomerStatus.ACTIVE
    credit_limit: Money = field(default_factory=lambda: Money(Decimal("5000.00")))
    outstanding_balance: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    tags: list[str] = field(default_factory=list)

    def can_accept_new_work(self, estimated_total: Money) -> bool:
        if self.status in {CustomerStatus.PAUSED, CustomerStatus.DELINQUENT}:
            return False
        projected = self.outstanding_balance.add(estimated_total)
        return projected.amount <= self.credit_limit.amount


@dataclass
class Technician:
    id: str
    name: str
    skills: set[TechnicianSkill]
    daily_capacity_hours: int = 8
    active: bool = True

    def can_handle(self, required_skills: set[TechnicianSkill], duration_hours: int) -> bool:
        return self.active and required_skills.issubset(self.skills) and duration_hours <= self.daily_capacity_hours


@dataclass
class InventoryItem:
    sku: str
    name: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: Money
    active: bool = True

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Reservation quantity must be positive.")
        if quantity > self.quantity_on_hand:
            raise ValueError(f"Insufficient stock for {self.sku}.")
        self.quantity_on_hand -= quantity

    def should_reorder(self) -> bool:
        return self.active and self.quantity_on_hand <= self.reorder_point


@dataclass
class RequiredPart:
    sku: str
    quantity: int


@dataclass
class WorkOrder:
    id: str
    customer_id: str
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    requested_date: date
    site_address: Address
    required_parts: list[RequiredPart] = field(default_factory=list)
    required_skills: set[TechnicianSkill] = field(default_factory=set)
    estimated_hours: int = 2
    assigned_technician_id: str | None = None
    scheduled_date: date | None = None
    completed_at: datetime | None = None
    labor_rate: Money = field(default_factory=lambda: Money(Decimal("95.00")))
    notes: list[str] = field(default_factory=list)

    def mark_ready(self) -> None:
        if self.status != WorkOrderStatus.DRAFT:
            return
        self.status = WorkOrderStatus.READY

    def schedule(self, technician_id: str, scheduled_date: date) -> None:
        if self.status not in {WorkOrderStatus.READY, WorkOrderStatus.SCHEDULED}:
            raise ValueError("Only ready work orders can be scheduled.")
        self.assigned_technician_id = technician_id
        self.scheduled_date = scheduled_date
        self.status = WorkOrderStatus.SCHEDULED

    def complete(self, completed_at: datetime, note: str | None = None) -> None:
        if self.status not in {WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS}:
            raise ValueError("Only scheduled or in-progress work orders can be completed.")
        self.status = WorkOrderStatus.COMPLETED
        self.completed_at = completed_at
        if note:
            self.notes.append(note)

    def estimated_labor_total(self) -> Money:
        return self.labor_rate.multiply(self.estimated_hours)


@dataclass
class InvoiceLine:
    description: str
    quantity: int
    unit_price: Money

    def total(self) -> Money:
        return self.unit_price.multiply(self.quantity)


@dataclass
class Invoice:
    id: str
    customer_id: str
    work_order_id: str
    status: InvoiceStatus
    issued_on: date | None
    due_on: date | None
    lines: list[InvoiceLine]

    def subtotal(self) -> Money:
        currency = self.lines[0].unit_price.currency if self.lines else "USD"
        total = Money(Decimal("0.00"), currency)
        for line in self.lines:
            total = total.add(line.total())
        return total

    def issue(self, issued_on: date, due_on: date) -> None:
        if not self.lines:
            raise ValueError("Cannot issue an invoice without line items.")
        self.issued_on = issued_on
        self.due_on = due_on
        self.status = InvoiceStatus.ISSUED
