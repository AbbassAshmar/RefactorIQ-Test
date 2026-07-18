from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.services.operations_facade import OperationsFacade
from nimbus_ops.interfaces.api.dependencies import get_operations_facade
from nimbus_ops.interfaces.api.schemas import (
    BacklogPriorityResponse,
    DispatchPlanResponse,
    LegacyDispatchManifestResponse,
    OperationsAdminResponse,
)

router = APIRouter()


@router.get("/operations/summary", response_model=OperationsAdminResponse)
def operations_summary(
    facade: OperationsFacade = Depends(get_operations_facade),
) -> OperationsAdminResponse:
    return OperationsAdminResponse(
        customers=len(facade.customer_service.list_customers()),
        work_orders=len(facade.work_order_service.list_work_orders()),
        assets=len(facade.asset_service.list_assets()),
        contracts=len(facade.contract_service.list_contracts()),
        invoices=len(facade.billing_service.list_invoices()),
        notifications=len(facade.notification_service.list_notifications()),
    )


@router.get("/operations/control-tower")
def control_tower_snapshot(
    facade: OperationsFacade = Depends(get_operations_facade),
) -> dict[str, object]:
    return facade.control_tower_snapshot()


@router.get("/operations/export")
def legacy_operations_export(
    facade: OperationsFacade = Depends(get_operations_facade),
) -> dict[str, object]:
    return facade.legacy_operations_export()


@router.get("/operations/dispatch-plan", response_model=DispatchPlanResponse)
def dispatch_plan(
    as_of: date | None = Query(default=None),
    horizon_days: int = Query(default=14, ge=1, le=90),
    include_scheduled: bool = Query(default=False),
    facade: OperationsFacade = Depends(get_operations_facade),
) -> DispatchPlanResponse:
    return DispatchPlanResponse.model_validate(
        facade.dispatch_plan(
            as_of=as_of,
            horizon_days=horizon_days,
            include_scheduled=include_scheduled,
        )
    )


@router.get(
    "/operations/backlog-priorities",
    response_model=list[BacklogPriorityResponse],
)
def backlog_priorities(
    as_of: date | None = Query(default=None),
    facade: OperationsFacade = Depends(get_operations_facade),
) -> list[BacklogPriorityResponse]:
    return [
        BacklogPriorityResponse.model_validate(candidate)
        for candidate in facade.backlog_priorities(as_of)
    ]


@router.get(
    "/operations/dispatch-manifest",
    response_model=LegacyDispatchManifestResponse,
)
def legacy_dispatch_manifest(
    as_of: date | None = Query(default=None),
    facade: OperationsFacade = Depends(get_operations_facade),
) -> LegacyDispatchManifestResponse:
    return LegacyDispatchManifestResponse.model_validate(
        facade.legacy_dispatch_manifest(as_of)
    )
