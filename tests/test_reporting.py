from __future__ import annotations

from fastapi.testclient import TestClient


def test_seeded_reference_data_is_available(client: TestClient) -> None:
    customers = client.get("/api/customers")
    inventory = client.get("/api/inventory")

    assert customers.status_code == 200
    assert inventory.status_code == 200
    assert {customer["id"] for customer in customers.json()} == {"cus_acme", "cus_levant"}
    assert any(item["should_reorder"] for item in inventory.json())


def test_operations_report_shape(client: TestClient) -> None:
    response = client.get("/api/reports/operations")

    assert response.status_code == 200
    report = response.json()
    assert "ready" in report["work_orders_by_status"]
    assert "emergency" in report["work_orders_by_priority"]
    assert isinstance(report["reorder_skus"], list)
