from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.application.services.reporting_service import ReportingService
from nimbus_ops.interfaces.api.dependencies import get_reporting_service
from nimbus_ops.interfaces.api.schemas import OperationsReportResponse

router = APIRouter()


@router.get("/operations", response_model=OperationsReportResponse)
def operations_report(service: ReportingService = Depends(get_reporting_service)) -> OperationsReportResponse:
    report = service.operations_report()
    return OperationsReportResponse(**report.__dict__)
