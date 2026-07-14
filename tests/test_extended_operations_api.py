from __future__ import annotations

from fastapi.testclient import TestClient


def test_asset_search_service_due_and_registration(client: TestClient) -> None:
    assets = client.get("/api/assets")
    due = client.get("/api/assets/due", params={"as_of": "2026-07-14"})
    created = client.post(
        "/api/assets",
        json={
            "customer_id": "cus_acme",
            "name": "Cooling tower",
            "serial_number": "COOL-ACME-007",
            "category": "hvac",
            "installed_on": "2026-06-01",
            "service_interval_days": 120,
            "site_address": "42 Industrial Way, Beirut",
        },
    )

    assert assets.status_code == 200
    assert len(assets.json()) == 2
    assert due.status_code == 200
    assert {asset["id"] for asset in due.json()} == {"asset_acme_generator"}
    assert created.status_code == 201
    assert created.json()["serial_number"] == "COOL-ACME-007"


def test_contract_coverage_and_expiry_queries(client: TestClient) -> None:
    contracts = client.get("/api/contracts")
    coverage = client.get(
        "/api/contracts/contract_acme_priority/coverage",
        params={"service_date": "2026-07-01"},
    )
    expiring = client.get(
        "/api/contracts/expiring",
        params={"days": 45, "as_of": "2026-07-01"},
    )

    assert contracts.status_code == 200
    assert len(contracts.json()) == 2
    assert coverage.json() == {
        "contract_id": "contract_acme_priority",
        "service_date": "2026-07-01",
        "covered": True,
    }
    assert expiring.status_code == 200
    assert [contract["id"] for contract in expiring.json()] == ["contract_levant_basic"]


def test_notifications_and_operations_admin_summary(client: TestClient) -> None:
    sent = client.post(
        "/api/notifications",
        json={
            "customer_id": "cus_levant",
            "channel": "email",
            "recipient": "facilities@levant.example",
            "subject": "Service window",
            "body": "Your next preventative maintenance window is ready to schedule.",
        },
    )
    notifications = client.get("/api/notifications", params={"customer_id": "cus_levant"})
    summary = client.get("/api/admin/operations/summary")
    control_tower = client.get("/api/admin/operations/control-tower")
    legacy_export = client.get("/api/admin/operations/export")

    assert sent.status_code == 201
    assert sent.json()["status"] == "sent"
    assert len(notifications.json()) == 1
    assert summary.status_code == 200
    assert summary.json()["customers"] == 2
    assert summary.json()["assets"] == 2
    assert summary.json()["contracts"] == 2
    assert summary.json()["notifications"] == 1
    assert control_tower.status_code == 200
    assert control_tower.json()["alert_count"] >= 0
    assert legacy_export.status_code == 200
    assert legacy_export.json()["totals"]["customers"] == 2
