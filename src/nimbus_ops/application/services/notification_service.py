from __future__ import annotations

from nimbus_ops.application.notification_dto import NotificationSummary, SendNotificationCommand
from nimbus_ops.application.notification_mappers import to_notification_summary
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.entities import new_id
from nimbus_ops.domain.exceptions import EntityNotFoundError
from nimbus_ops.domain.notifications import Notification


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


class NotificationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("notification service")

    def list_notifications(self, customer_id: str | None = None) -> list[NotificationSummary]:
        with self.uow as uow:
            return [
                to_notification_summary(notification)
                for notification in uow.notifications.list(customer_id)
            ]

    def get_notification(self, notification_id: str) -> NotificationSummary:
        with self.uow as uow:
            notification = _require_entity(
                uow.notifications.get(notification_id),
                "Notification",
                notification_id,
            )
            return to_notification_summary(notification)

    def send(self, command: SendNotificationCommand) -> NotificationSummary:
        with self.uow as uow:
            customer = _require_entity(uow.customers.get(command.customer_id), "Customer", command.customer_id)
            notification = Notification(
                id=new_id("notification"),
                customer_id=customer.id,
                channel=command.channel,
                recipient=command.recipient,
                subject=command.subject,
                body=command.body,
            )
            notification.mark_sent()
            uow.notifications.save(notification)
            uow.commit()
            return to_notification_summary(notification)

    def retry_queued(self) -> list[NotificationSummary]:
        with self.uow as uow:
            queued = []
            for notification in uow.notifications.list():
                if notification.status.value == "queued":
                    notification.mark_sent()
                    uow.notifications.save(notification)
                    queued.append(notification)
            uow.commit()
            return [to_notification_summary(notification) for notification in queued]
