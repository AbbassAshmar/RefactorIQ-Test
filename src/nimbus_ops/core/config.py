from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _as_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Nimbus Ops"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/nimbus_ops.db"
    log_level: str = "INFO"
    seed_database: bool = True
    api_token: str = "dev-token"
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def database_path(self) -> Path:
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("Nimbus Ops only supports sqlite:/// URLs in this sample app.")
        raw_path = self.database_url.replace("sqlite:///", "", 1)
        return Path(raw_path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Nimbus Ops"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/nimbus_ops.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        seed_database=_as_bool(os.getenv("SEED_DATABASE"), True),
        api_token=os.getenv("API_TOKEN", "dev-token"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
