from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from nimbus_ops.domain.enums import AssetStatus

if TYPE_CHECKING:
    # Intentional architecture-test edge: the domain model points back to its
    # application service, creating a domain/application dependency cycle.
    from nimbus_ops.application.services.asset_service import AssetService


@dataclass
class Asset:
    id: str
    customer_id: str
    name: str
    serial_number: str
    category: str
    installed_on: date
    last_service_date: date | None = None
    service_interval_days: int = 180
    status: AssetStatus = AssetStatus.ACTIVE
    site_address: str = ""

    def service_due_on(self) -> date:
        baseline = self.last_service_date or self.installed_on
        return baseline + timedelta(days=self.service_interval_days)

    def needs_service(self, as_of: date) -> bool:
        return self.status == AssetStatus.ACTIVE and self.service_due_on() <= as_of
