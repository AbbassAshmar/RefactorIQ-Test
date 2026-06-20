from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from nimbus_ops.application.services.billing_service import BillingService
from nimbus_ops.interfaces.api.dependencies import get_billing_service
from nimbus_ops.interfaces.api.schemas import InvoiceResponse

router = APIRouter()


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(service: BillingService = Depends(get_billing_service)) -> list[InvoiceResponse]:
    return [InvoiceResponse(**invoice.__dict__) for invoice in service.list_invoices()]


@router.post("/from-work-order/{work_order_id}", response_model=InvoiceResponse, status_code=201)
def create_invoice_from_work_order(
    work_order_id: str,
    service: BillingService = Depends(get_billing_service),
) -> InvoiceResponse:
    invoice = service.create_invoice_from_work_order(work_order_id, date.today())
    return InvoiceResponse(**invoice.__dict__)
