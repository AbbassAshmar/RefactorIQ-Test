from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.application.services.inventory_service import InventoryService
from nimbus_ops.interfaces.api.dependencies import get_inventory_service
from nimbus_ops.interfaces.api.schemas import InventoryResponse, StockAdjustmentPayload

router = APIRouter()


@router.get("", response_model=list[InventoryResponse])
def list_inventory(service: InventoryService = Depends(get_inventory_service)) -> list[InventoryResponse]:
    return [InventoryResponse(**item.__dict__) for item in service.list_inventory_health()]


@router.post("/{sku}/adjust", response_model=InventoryResponse)
def adjust_stock(
    sku: str,
    payload: StockAdjustmentPayload,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    return InventoryResponse(**service.adjust_stock(sku, payload.delta).__dict__)
