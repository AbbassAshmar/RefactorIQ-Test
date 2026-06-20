# Nimbus Ops

Nimbus Ops is a realistic FastAPI sample application built as a scan target for
RefactorIQ. It models a field-service company that manages customers, work
orders, technician dispatching, inventory, invoicing, and operational reports.

The code intentionally uses a clean architecture layout:

- `domain`: entities, value objects, policies, exceptions, and domain events.
- `application`: use cases, DTOs, ports, and workflow orchestration.
- `infrastructure`: SQLite repositories, persistence setup, seed data, and event
  publishing.
- `interfaces`: FastAPI routers, API schemas, dependencies, and error handling.

It is not a tiny toy project. It has nested folders, cross-module imports,
classes, functions, orchestration services, validation, tests, and enough
business logic to exercise static metrics, dependency analysis, duplication
checks, and blast-radius scoring.

## Run Locally

```powershell
cd refactor-iq-test
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m nimbus_ops.main
```

The API starts at `http://127.0.0.1:8000`.

Useful endpoints:

- `GET /health`
- `GET /api/customers`
- `POST /api/work-orders`
- `POST /api/work-orders/{work_order_id}/schedule`
- `POST /api/work-orders/{work_order_id}/complete`
- `POST /api/invoices/from-work-order/{work_order_id}`
- `GET /api/reports/operations`

## Tests

```powershell
pytest
```

## Example Request

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/work-orders `
  -ContentType "application/json" `
  -Body '{
    "customer_id": "cus_acme",
    "title": "Quarterly generator maintenance",
    "description": "Inspect generators and replace filters.",
    "priority": "high",
    "requested_date": "2026-06-20",
    "site_address": {
      "line1": "42 Industrial Way",
      "city": "Beirut",
      "country": "LB",
      "postal_code": "1107"
    },
    "required_skus": [{"sku": "FILTER-10", "quantity": 2}]
  }'
```

## Notes For RefactorIQ Scanning

- `application/services/work_order_service.py` contains orchestration logic with
  branching business rules.
- `domain/policies.py` has dense decision logic for complexity metrics.
- `infrastructure/repositories.py` is intentionally central and high fan-in.
- `application/services/reporting_service.py` contains similar aggregation
  functions to give duplication and refactoring-benefit layers useful signals.
