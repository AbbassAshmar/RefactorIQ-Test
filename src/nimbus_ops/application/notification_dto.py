from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nimbus_ops.domain.enums import NotificationChannel, NotificationStatus


@dataclass(frozen=True)
class SendNotificationCommand:
    customer_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class NotificationSummary:
    id: str
    customer_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None

