from __future__ import annotations

from enum import StrEnum


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELINQUENT = "delinquent"


class WorkOrderPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


class WorkOrderStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class TechnicianSkill(StrEnum):
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    PLUMBING = "plumbing"
    SAFETY = "safety"
    NETWORKING = "networking"
