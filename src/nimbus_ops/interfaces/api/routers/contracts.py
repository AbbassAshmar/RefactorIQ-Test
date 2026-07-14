from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.contract_dto import CreateContractCommand
from nimbus_ops.application.services.contract_service import ContractService
from nimbus_ops.interfaces.api.dependencies import get_contract_service
from nimbus_ops.interfaces.api.schemas import (
    ContractCoverageResponse,
    ContractResponse,
    CreateContractPayload,
)

router = APIRouter()


@router.get("/expiring", response_model=list[ContractResponse])
def expiring_contracts(
    days: int = Query(default=30, ge=1, le=365),
    as_of: date | None = Query(default=None),
    service: ContractService = Depends(get_contract_service),
) -> list[ContractResponse]:
    return [
        ContractResponse(**contract.__dict__)
        for contract in service.expiring_soon(days, as_of)
    ]


@router.get("", response_model=list[ContractResponse])
def list_contracts(
    customer_id: str | None = Query(default=None),
    query: str | None = Query(default=None),
    service: ContractService = Depends(get_contract_service),
) -> list[ContractResponse]:
    return [
        ContractResponse(**contract.__dict__)
        for contract in service.list_contracts(customer_id, query)
    ]


@router.post("", response_model=ContractResponse, status_code=201)
def create_contract(
    payload: CreateContractPayload,
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    contract = service.create_contract(CreateContractCommand(**payload.model_dump()))
    return ContractResponse(**contract.__dict__)


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: str, service: ContractService = Depends(get_contract_service)) -> ContractResponse:
    return ContractResponse(**service.get_contract(contract_id).__dict__)


@router.get("/{contract_id}/coverage", response_model=ContractCoverageResponse)
def contract_coverage(
    contract_id: str,
    service_date: date = Query(...),
    service: ContractService = Depends(get_contract_service),
) -> ContractCoverageResponse:
    return ContractCoverageResponse(
        contract_id=contract_id,
        service_date=service_date,
        covered=service.is_covered(contract_id, service_date),
    )

