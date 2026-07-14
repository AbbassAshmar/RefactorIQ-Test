from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from nimbus_ops.application.services.customer_service import CustomerService
from nimbus_ops.interfaces.api.dependencies import get_customer_service
from nimbus_ops.interfaces.api.schemas import CustomerResponse

router = APIRouter()


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    query: str | None = Query(default=None),
    service: CustomerService = Depends(get_customer_service),
) -> list[CustomerResponse]:
    customers = service.list_customers(query)
    return [
        CustomerResponse(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            status=customer.status.value,
            credit_limit=customer.credit_limit.amount,
            outstanding_balance=customer.outstanding_balance.amount,
            tags=customer.tags,
        )
        for customer in customers
    ]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: str, service: CustomerService = Depends(get_customer_service)) -> CustomerResponse:
    customer = service.get_customer(customer_id)
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        status=customer.status.value,
        credit_limit=customer.credit_limit.amount,
        outstanding_balance=customer.outstanding_balance.amount,
        tags=customer.tags,
    )
