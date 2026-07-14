from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.asset_dto import RegisterAssetCommand
from nimbus_ops.application.services.asset_service import AssetService
from nimbus_ops.interfaces.api.dependencies import get_asset_service
from nimbus_ops.interfaces.api.schemas import (
    AssetResponse,
    RecordAssetServicePayload,
    RegisterAssetPayload,
)

router = APIRouter()


@router.get("/due", response_model=list[AssetResponse])
def due_assets(
    as_of: date | None = Query(default=None),
    service: AssetService = Depends(get_asset_service),
) -> list[AssetResponse]:
    return [AssetResponse(**asset.__dict__) for asset in service.due_for_service(as_of or date.today())]


@router.get("", response_model=list[AssetResponse])
def list_assets(
    customer_id: str | None = Query(default=None),
    query: str | None = Query(default=None),
    service: AssetService = Depends(get_asset_service),
) -> list[AssetResponse]:
    return [AssetResponse(**asset.__dict__) for asset in service.list_assets(customer_id, query)]


@router.post("", response_model=AssetResponse, status_code=201)
def register_asset(
    payload: RegisterAssetPayload,
    service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    asset = service.register_asset(RegisterAssetCommand(**payload.model_dump()))
    return AssetResponse(**asset.__dict__)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, service: AssetService = Depends(get_asset_service)) -> AssetResponse:
    return AssetResponse(**service.get_asset(asset_id).__dict__)


@router.post("/{asset_id}/service", response_model=AssetResponse)
def record_asset_service(
    asset_id: str,
    payload: RecordAssetServicePayload,
    service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    return AssetResponse(**service.record_service(asset_id, payload.serviced_on).__dict__)

