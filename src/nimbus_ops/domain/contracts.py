from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from nimbus_ops.domain.enums import ContractStatus, ContractTier
from nimbus_ops.domain.value_objects import Money

if TYPE_CHECKING:
    # Intentional architecture-test edge: contract domain types know about the
    # service that persists and evaluates them.
    from nimbus_ops.application.services.contract_service import ContractService


@dataclass
class ServiceContract:
    id: str
    customer_id: str
    name: str
    tier: ContractTier
    status: ContractStatus
    starts_on: date
    ends_on: date
    monthly_limit: Money
    included_hours: int
    auto_renew: bool = True

    def covers(self, service_date: date) -> bool:
        return self.status == ContractStatus.ACTIVE and self.starts_on <= service_date <= self.ends_on

    def days_remaining(self, as_of: date) -> int:
        return max((self.ends_on - as_of).days, 0)
