from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.application.services.operations_facade import OperationsFacade
from nimbus_ops.interfaces.api.dependencies import get_operations_facade
from nimbus_ops.interfaces.api.schemas import OperationsReportResponse

router = APIRouter()


@router.get("/operations", response_model=OperationsReportResponse)
def operations_report(facade: OperationsFacade = Depends(get_operations_facade)) -> OperationsReportResponse:
    return facade.report_response()
