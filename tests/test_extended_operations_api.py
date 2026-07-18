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


def test_dispatch_plan_escalates_sla_breaches_and_prioritizes_backlog(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/work-orders",
        json={
            "customer_id": "cus_acme",
            "title": "Emergency generator inspection",
            "description": "Investigate repeated generator alarms before the next outage window.",
            "priority": "high",
            "requested_date": "2026-07-01",
            "site_address": {
                "line1": "42 Industrial Way",
                "city": "Beirut",
                "country": "LB",
                "postal_code": "1107",
            },
            "required_skus": [{"sku": "FILTER-10", "quantity": 2}],
            "required_skills": ["electrical", "safety"],
            "estimated_hours": 4,
        },
    )
    dispatch_plan = client.get(
        "/api/admin/operations/dispatch-plan",
        params={"as_of": "2026-07-18", "horizon_days": 7},
    )
    backlog = client.get(
        "/api/admin/operations/backlog-priorities",
        params={"as_of": "2026-07-18"},
    )
    dispatch_manifest = client.get(
        "/api/admin/operations/dispatch-manifest",
        params={"as_of": "2026-07-18"},
    )
    invalid_horizon = client.get(
        "/api/admin/operations/dispatch-plan",
        params={"as_of": "2026-07-18", "horizon_days": 91},
    )
    extended_horizon = client.get(
        "/api/admin/operations/dispatch-plan",
        params={"as_of": "2026-07-18", "horizon_days": 15},
    )

    assert created.status_code == 201
    work_order_id = created.json()["id"]
    assert dispatch_plan.status_code == 200
    payload = dispatch_plan.json()
    assert payload["summary"] == {
        "total": 1,
        "ready": 0,
        "blocked": 0,
        "escalated": 1,
        "sla_breaches": 1,
        "orders_with_shortages": 0,
        "orders_without_technicians": 0,
        "estimated_costs": {"USD": 417.0},
    }
    escalated = payload["queues"]["escalated"][0]
    assert escalated["work_order_id"] == work_order_id
    assert escalated["sla_due_on"] == "2026-07-02"
    assert escalated["breach_days"] == 16
    assert escalated["recommended_technician_id"] == "tech_maya"
    assert escalated["covered_contract_ids"] == ["contract_acme_priority"]
    assert escalated["overdue_asset_ids"] == ["asset_acme_generator"]
    assert len(payload["capacity_forecast"]) == 7

    assert backlog.status_code == 200
    assert backlog.json()[0]["work_order_id"] == work_order_id
    assert backlog.json()[0]["priority_score"] == 65
    assert dispatch_manifest.status_code == 200
    assert dispatch_manifest.json()["totals"] == {
        "orders": 1,
        "ready": 0,
        "blocked": 0,
        "escalated": 1,
    }
    manifest_row = dispatch_manifest.json()["rows"][0]
    assert manifest_row["work_order_id"] == work_order_id
    assert manifest_row["sla_due_on"] == "2026-07-02"
    assert manifest_row["queue"] == "escalated"
    assert manifest_row["estimated_costs"] == {"USD": 417.0}
    assert invalid_horizon.status_code == 422
    assert len(extended_horizon.json()["capacity_forecast"]) == 15


def test_dispatch_plan_honors_reserved_stock_and_current_assignment(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/work-orders",
        json={
            "customer_id": "cus_acme",
            "title": "Generator load-bank test",
            "description": "Run the annual load-bank test with the reserved service kit.",
            "priority": "normal",
            "requested_date": "2026-07-18",
            "site_address": {
                "line1": "42 Industrial Way",
                "city": "Beirut",
                "country": "LB",
                "postal_code": "1107",
            },
            "required_skus": [{"sku": "FILTER-10", "quantity": 20}],
            "required_skills": ["electrical", "safety"],
            "estimated_hours": 10,
        },
    )
    work_order_id = created.json()["id"]
    scheduled = client.post(
        f"/api/work-orders/{work_order_id}/schedule",
        json={
            "scheduled_date": "2026-07-18",
            "unavailable_technician_ids": [],
        },
    )
    dispatch_plan = client.get(
        "/api/admin/operations/dispatch-plan",
        params={
            "as_of": "2026-07-18",
            "horizon_days": 7,
            "include_scheduled": True,
        },
    )
    dispatch_manifest = client.get(
        "/api/admin/operations/dispatch-manifest",
        params={"as_of": "2026-07-18"},
    )
    backlog = client.get(
        "/api/admin/operations/backlog-priorities",
        params={"as_of": "2026-07-18"},
    )

    assert created.status_code == 201
    assert scheduled.status_code == 200
    assert scheduled.json()["assigned_technician_id"] == "tech_maya"
    assert dispatch_plan.status_code == 200
    payload = dispatch_plan.json()
    assert payload["summary"]["ready"] == 1
    planned_order = payload["queues"]["ready"][0]
    assert planned_order["work_order_id"] == work_order_id
    assert planned_order["blockers"] == []
    assert planned_order["shortages"] == []
    assert planned_order["recommended_technician_id"] == "tech_maya"
    assert planned_order["technician_options"][0] == {
        "technician_id": "tech_maya",
        "available_hours": 0,
    }

    assert dispatch_manifest.status_code == 200
    manifest_row = dispatch_manifest.json()["rows"][0]
    assert manifest_row["work_order_id"] == work_order_id
    assert manifest_row["queue"] == "ready"
    assert manifest_row["blockers"] == []
    assert backlog.status_code == 200
    assert backlog.json() == []


def test_dispatch_plan_allocates_capacity_by_sla_before_repository_order(
    client: TestClient,
) -> None:
    common_payload = {
        "customer_id": "cus_acme",
        "description": "Allocate the only qualified technician using operational priority.",
        "site_address": {
            "line1": "42 Industrial Way",
            "city": "Beirut",
            "country": "LB",
            "postal_code": "1107",
        },
        "required_skus": [],
        "required_skills": ["electrical", "safety"],
        "estimated_hours": 10,
    }
    high_priority = client.post(
        "/api/work-orders",
        json={
            **common_payload,
            "title": "Overdue generator safety inspection",
            "priority": "high",
            "requested_date": "2026-07-10",
        },
    )
    newer_low_priority = client.post(
        "/api/work-orders",
        json={
            **common_payload,
            "title": "Routine generator label replacement",
            "priority": "low",
            "requested_date": "2026-07-17",
        },
    )
    dispatch_plan = client.get(
        "/api/admin/operations/dispatch-plan",
        params={"as_of": "2026-07-18", "horizon_days": 1},
    )

    assert high_priority.status_code == 201
    assert newer_low_priority.status_code == 201
    assert dispatch_plan.status_code == 200
    payload = dispatch_plan.json()
    escalated = payload["queues"]["escalated"][0]
    blocked = payload["queues"]["blocked"][0]
    assert escalated["work_order_id"] == high_priority.json()["id"]
    assert escalated["recommended_technician_id"] == "tech_maya"
    assert blocked["work_order_id"] == newer_low_priority.json()["id"]
    assert blocked["recommended_technician_id"] is None
    assert "technician_unavailable" in blocked["blockers"]
