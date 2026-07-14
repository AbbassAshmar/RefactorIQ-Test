from __future__ import annotations

from nimbus_ops.application.notification_dto import NotificationSummary
from nimbus_ops.domain.notifications import Notification


def to_notification_summary(notification: Notification) -> NotificationSummary:
    return NotificationSummary(
        id=notification.id,
        customer_id=notification.customer_id,
        channel=notification.channel,
        recipient=notification.recipient,
        subject=notification.subject,
        body=notification.body,
        status=notification.status,
        created_at=notification.created_at,
        sent_at=notification.sent_at,
    )

