from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from nimbus_ops.domain.enums import AssetStatus


@dataclass(frozen=True)
class RegisterAssetCommand:
    customer_id: str
    name: str
    serial_number: str
    category: str
    installed_on: date
    service_interval_days: int
    site_address: str


@dataclass(frozen=True)
class AssetSummary:
    id: str
    customer_id: str
    name: str
    serial_number: str
    category: str
    installed_on: date
    service_due_on: date
    status: AssetStatus
    site_address: str

