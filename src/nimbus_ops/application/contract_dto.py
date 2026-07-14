from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from nimbus_ops.domain.enums import ContractStatus, ContractTier


@dataclass(frozen=True)
class CreateContractCommand:
    customer_id: str
    name: str
    tier: ContractTier
    starts_on: date
    ends_on: date
    monthly_limit: Decimal
    included_hours: int
    auto_renew: bool


@dataclass(frozen=True)
class ContractSummary:
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

