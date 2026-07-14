from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.interfaces.api.dependencies import require_api_token
from nimbus_ops.interfaces.api.routers import (
    admin,
    assets,
    contracts,
    customers,
    health,
    inventory,
    invoices,
    notifications,
    reports,
    work_orders,
)

api_router = APIRouter(dependencies=[Depends(require_api_token)])
api_router.include_router(health.router)
api_router.include_router(customers.router, prefix="/api/customers", tags=["customers"])
api_router.include_router(work_orders.router, prefix="/api/work-orders", tags=["work-orders"])
api_router.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
api_router.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
api_router.include_router(reports.router, prefix="/api/reports", tags=["reports"])
api_router.include_router(assets.router, prefix="/api/assets", tags=["assets"])
api_router.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
api_router.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
api_router.include_router(admin.router, prefix="/api/admin", tags=["admin"])
