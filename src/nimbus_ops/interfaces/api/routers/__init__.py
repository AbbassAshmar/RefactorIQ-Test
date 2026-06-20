from __future__ import annotations

from fastapi import APIRouter, Depends

from nimbus_ops.interfaces.api.dependencies import require_api_token
from nimbus_ops.interfaces.api.routers import customers, health, inventory, invoices, reports, work_orders

api_router = APIRouter(dependencies=[Depends(require_api_token)])
api_router.include_router(health.router)
api_router.include_router(customers.router, prefix="/api/customers", tags=["customers"])
api_router.include_router(work_orders.router, prefix="/api/work-orders", tags=["work-orders"])
api_router.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
api_router.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
api_router.include_router(reports.router, prefix="/api/reports", tags=["reports"])
