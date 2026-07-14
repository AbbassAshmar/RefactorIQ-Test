from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.notification_dto import SendNotificationCommand
from nimbus_ops.application.services.notification_service import NotificationService
from nimbus_ops.interfaces.api.dependencies import get_notification_service
from nimbus_ops.interfaces.api.schemas import NotificationResponse, SendNotificationPayload

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    customer_id: str | None = Query(default=None),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationResponse]:
    return [
        NotificationResponse(**notification.__dict__)
        for notification in service.list_notifications(customer_id)
    ]


@router.post("", response_model=NotificationResponse, status_code=201)
def send_notification(
    payload: SendNotificationPayload,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    notification = service.send(SendNotificationCommand(**payload.model_dump()))
    return NotificationResponse(**notification.__dict__)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    return NotificationResponse(**service.get_notification(notification_id).__dict__)


@router.post("/retry", response_model=list[NotificationResponse])
def retry_notifications(
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationResponse]:
    return [
        NotificationResponse(**notification.__dict__)
        for notification in service.retry_queued()
    ]

