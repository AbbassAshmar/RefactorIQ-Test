from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_schedule_complete_and_invoice_work_order(client: TestClient) -> None:
    create_response = client.post(
        "/api/work-orders",
        json={
            "customer_id": "cus_acme",
            "title": "Replace generator filters",
            "description": "Replace oil filters and inspect breaker panel.",
            "priority": "high",
            "requested_date": "2026-06-20",
            "site_address": {
                "line1": "42 Industrial Way",
                "city": "Beirut",
                "country": "LB",
                "postal_code": "1107",
            },
            "required_skus": [{"sku": "FILTER-10", "quantity": 2}],
            "required_skills": ["electrical", "safety"],
            "estimated_hours": 3,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "ready"

    schedule_response = client.post(
        f"/api/work-orders/{created['id']}/schedule",
        json={"scheduled_date": "2026-06-21", "unavailable_technician_ids": []},
    )
    assert schedule_response.status_code == 200
    scheduled = schedule_response.json()
    assert scheduled["status"] == "scheduled"
    assert scheduled["assigned_technician_id"] == "tech_maya"

    complete_response = client.post(
        f"/api/work-orders/{created['id']}/complete",
        json={"completed_at": "2026-06-21T12:30:00+00:00", "note": "Customer signed off."},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    invoice_response = client.post(f"/api/invoices/from-work-order/{created['id']}")
    assert invoice_response.status_code == 201
    invoice = invoice_response.json()
    assert invoice["work_order_id"] == created["id"]
    assert invoice["status"] == "issued"
    assert float(invoice["total"]) > 0


def test_inventory_shortage_returns_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/work-orders",
        json={
            "customer_id": "cus_acme",
            "title": "Oversized inventory request",
            "description": "Try to reserve more filters than the warehouse has.",
            "priority": "normal",
            "requested_date": "2026-06-20",
            "site_address": {
                "line1": "42 Industrial Way",
                "city": "Beirut",
                "country": "LB",
                "postal_code": "1107",
            },
            "required_skus": [{"sku": "FILTER-10", "quantity": 1000}],
            "required_skills": ["electrical"],
            "estimated_hours": 2,
        },
    )

    assert response.status_code == 409
    assert response.json()["error"] == "business_rule_failed"
