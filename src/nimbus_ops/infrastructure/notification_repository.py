from __future__ import annotations

import sqlite3
from datetime import datetime

from nimbus_ops.domain.enums import NotificationChannel, NotificationStatus
from nimbus_ops.domain.notifications import Notification


class SQLiteNotificationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, notification_id: str) -> Notification | None:
        row = self.connection.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self, customer_id: str | None = None) -> list[Notification]:
        if customer_id:
            rows = self.connection.execute(
                "SELECT * FROM notifications WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, notification: Notification) -> None:
        self.connection.execute(
            """
            INSERT INTO notifications (
                id, customer_id, channel, recipient, subject, body, status,
                created_at, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                sent_at = excluded.sent_at,
                body = excluded.body
            """,
            (
                notification.id,
                notification.customer_id,
                notification.channel.value,
                notification.recipient,
                notification.subject,
                notification.body,
                notification.status.value,
                notification.created_at.isoformat(),
                notification.sent_at.isoformat() if notification.sent_at else None,
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> Notification:
        return Notification(
            id=row["id"],
            customer_id=row["customer_id"],
            channel=NotificationChannel(row["channel"]),
            recipient=row["recipient"],
            subject=row["subject"],
            body=row["body"],
            status=NotificationStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
        )

