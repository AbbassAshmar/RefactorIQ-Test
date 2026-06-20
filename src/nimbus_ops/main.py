from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from nimbus_ops.core.config import Settings, get_settings
from nimbus_ops.core.logging import configure_logging
from nimbus_ops.infrastructure.database import initialize_database
from nimbus_ops.infrastructure.seed import seed_database
from nimbus_ops.interfaces.api.error_handlers import register_error_handlers
from nimbus_ops.interfaces.api.routers import api_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    initialize_database(resolved_settings.database_path)
    if resolved_settings.seed_database:
        seed_database(resolved_settings.database_path)

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        description="Field-service operations API used as a realistic RefactorIQ scan target.",
    )
    app.dependency_overrides[get_settings] = lambda: resolved_settings
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "nimbus_ops.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    run()
