from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from nimbus_ops.domain.enums import NotificationChannel, NotificationStatus

if TYPE_CHECKING:
    # Intentional architecture-test edge for the notification domain cycle.
    from nimbus_ops.application.services.notification_service import NotificationService


@dataclass
class Notification:
    id: str
    customer_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    status: NotificationStatus = NotificationStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None

    def mark_sent(self, sent_at: datetime | None = None) -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = sent_at or datetime.now(timezone.utc)
