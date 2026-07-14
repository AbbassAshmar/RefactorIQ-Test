from __future__ import annotations

from fastapi.testclient import TestClient


def test_customer_detail_and_missing_customer(client: TestClient) -> None:
    found = client.get("/api/customers/cus_acme")
    missing = client.get("/api/customers/cus_missing")

    assert found.status_code == 200
    assert found.json()["email"] == "ops@acme.example"
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"
    assert missing.json()["entity"] == "Customer"


def test_inventory_adjustment_and_negative_stock_validation(client: TestClient) -> None:
    adjusted = client.post("/api/inventory/FILTER-10/adjust", json={"delta": -3})
    invalid = client.post("/api/inventory/FILTER-10/adjust", json={"delta": -1000})

    assert adjusted.status_code == 200
    assert adjusted.json()["quantity_on_hand"] == 29
    assert invalid.status_code == 422
    assert invalid.json()["error"] == "invalid_request"


def test_missing_work_order_paths_return_not_found(client: TestClient) -> None:
    schedule = client.post(
        "/api/work-orders/wo_missing/schedule",
        json={"scheduled_date": "2026-06-21", "unavailable_technician_ids": []},
    )
    complete = client.post(
        "/api/work-orders/wo_missing/complete",
        json={"completed_at": "2026-06-21T12:30:00+00:00"},
    )
    invoice = client.post("/api/invoices/from-work-order/wo_missing")

    assert schedule.status_code == 404
    assert complete.status_code == 404
    assert invoice.status_code == 404
