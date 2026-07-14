from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from nimbus_ops.application.services.asset_service import AssetService
from nimbus_ops.application.services.billing_service import BillingService
from nimbus_ops.application.services.customer_service import CustomerService
from nimbus_ops.application.services.contract_service import ContractService
from nimbus_ops.application.services.inventory_service import InventoryService
from nimbus_ops.application.services.notification_service import NotificationService
from nimbus_ops.application.services.operations_facade import OperationsFacade
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


def get_operations_facade(uow: SQLiteUnitOfWork = Depends(get_uow)) -> OperationsFacade:
    return OperationsFacade(uow)


def get_customer_service(facade: OperationsFacade = Depends(get_operations_facade)) -> CustomerService:
    return facade.customer_service


def get_asset_service(facade: OperationsFacade = Depends(get_operations_facade)) -> AssetService:
    return facade.asset_service


def get_contract_service(facade: OperationsFacade = Depends(get_operations_facade)) -> ContractService:
    return facade.contract_service


def get_notification_service(facade: OperationsFacade = Depends(get_operations_facade)) -> NotificationService:
    return facade.notification_service


def get_work_order_service(facade: OperationsFacade = Depends(get_operations_facade)) -> WorkOrderService:
    return facade.work_order_service


def get_inventory_service(facade: OperationsFacade = Depends(get_operations_facade)) -> InventoryService:
    return facade.inventory_service


def get_billing_service(facade: OperationsFacade = Depends(get_operations_facade)) -> BillingService:
    return facade.billing_service


def get_reporting_service(facade: OperationsFacade = Depends(get_operations_facade)) -> ReportingService:
    return facade.reporting_service
