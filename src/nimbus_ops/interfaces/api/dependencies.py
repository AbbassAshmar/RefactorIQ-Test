from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from nimbus_ops.application.services.billing_service import BillingService
from nimbus_ops.application.services.customer_service import CustomerService
from nimbus_ops.application.services.inventory_service import InventoryService
from nimbus_ops.application.services.reporting_service import ReportingService
from nimbus_ops.application.services.work_order_service import WorkOrderService
from nimbus_ops.core.config import Settings, get_settings
from nimbus_ops.core.security import token_matches
from nimbus_ops.infrastructure.repositories import SQLiteUnitOfWork


def require_api_token(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.app_env == "development" and authorization is None:
        return
    if not token_matches(authorization, settings.api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token.")


def get_uow(settings: Settings = Depends(get_settings)) -> SQLiteUnitOfWork:
    return SQLiteUnitOfWork(settings.database_path)


def get_customer_service(uow: SQLiteUnitOfWork = Depends(get_uow)) -> CustomerService:
    return CustomerService(uow)


def get_work_order_service(uow: SQLiteUnitOfWork = Depends(get_uow)) -> WorkOrderService:
    return WorkOrderService(uow)


def get_inventory_service(uow: SQLiteUnitOfWork = Depends(get_uow)) -> InventoryService:
    return InventoryService(uow)


def get_billing_service(uow: SQLiteUnitOfWork = Depends(get_uow)) -> BillingService:
    return BillingService(uow)


def get_reporting_service(uow: SQLiteUnitOfWork = Depends(get_uow)) -> ReportingService:
    return ReportingService(uow)
