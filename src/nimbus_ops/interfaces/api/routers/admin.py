from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.application.services.operations_facade import OperationsFacade
from nimbus_ops.interfaces.api.dependencies import get_operations_facade
from nimbus_ops.interfaces.api.schemas import OperationsAdminResponse

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
