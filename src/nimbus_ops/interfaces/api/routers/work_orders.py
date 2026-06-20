from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.dto import CompleteWorkOrderCommand, CreateWorkOrderCommand, RequiredPartDTO, ScheduleWorkOrderCommand
from nimbus_ops.application.services.work_order_service import WorkOrderService
from nimbus_ops.domain.value_objects import Address
from nimbus_ops.interfaces.api.dependencies import get_work_order_service
from nimbus_ops.interfaces.api.schemas import (
    CompleteWorkOrderPayload,
    CreateWorkOrderPayload,
    ScheduleWorkOrderPayload,
    WorkOrderResponse,
)

router = APIRouter()


@router.get("", response_model=list[WorkOrderResponse])
def list_work_orders(
    status: str | None = Query(default=None),
    service: WorkOrderService = Depends(get_work_order_service),
) -> list[WorkOrderResponse]:
    return [WorkOrderResponse(**summary.__dict__) for summary in service.list_work_orders(status)]


@router.post("", response_model=WorkOrderResponse, status_code=201)
def create_work_order(
    payload: CreateWorkOrderPayload,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    command = CreateWorkOrderCommand(
        customer_id=payload.customer_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        requested_date=payload.requested_date,
        site_address=Address(**payload.site_address.model_dump()),
        required_parts=[RequiredPartDTO(sku=part.sku, quantity=part.quantity) for part in payload.required_skus],
        required_skills=payload.required_skills,
        estimated_hours=payload.estimated_hours,
    )
    summary = service.create_work_order(command)
    return WorkOrderResponse(**summary.__dict__)


@router.post("/{work_order_id}/schedule", response_model=WorkOrderResponse)
def schedule_work_order(
    work_order_id: str,
    payload: ScheduleWorkOrderPayload,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    summary = service.schedule_work_order(
        ScheduleWorkOrderCommand(
            work_order_id=work_order_id,
            scheduled_date=payload.scheduled_date,
            unavailable_technician_ids=payload.unavailable_technician_ids,
        )
    )
    return WorkOrderResponse(**summary.__dict__)


@router.post("/{work_order_id}/complete", response_model=WorkOrderResponse)
def complete_work_order(
    work_order_id: str,
    payload: CompleteWorkOrderPayload,
    service: WorkOrderService = Depends(get_work_order_service),
) -> WorkOrderResponse:
    summary = service.complete_work_order(
        CompleteWorkOrderCommand(
            work_order_id=work_order_id,
            completed_at=payload.completed_at or datetime.now(timezone.utc),
            note=payload.note,
        )
    )
    return WorkOrderResponse(**summary.__dict__)
