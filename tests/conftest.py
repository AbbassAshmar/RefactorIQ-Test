from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbus_ops.core.config import Settings
from nimbus_ops.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        seed_database=True,
        api_token="test-token",
    )
    app = create_app(settings)
    return TestClient(app, headers={"Authorization": "Bearer test-token"})
