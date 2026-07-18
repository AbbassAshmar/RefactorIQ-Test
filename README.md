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
- `GET /api/assets` and `POST /api/assets`
- `GET /api/assets/due`
- `GET /api/contracts` and `POST /api/contracts`
- `GET /api/contracts/{contract_id}/coverage`
- `GET /api/notifications` and `POST /api/notifications`
- `GET /api/admin/operations/summary`
- `GET /api/admin/operations/control-tower`
- `GET /api/admin/operations/dispatch-plan`
- `GET /api/admin/operations/backlog-priorities`
- `GET /api/admin/operations/dispatch-manifest`
- `GET /api/admin/operations/export`

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
- Several application services intentionally repeat `_require_entity` and
  `_sort_named_records` instead of sharing helpers; these are exact duplication
  candidates.
- `billing_service.py` and `reporting_service.py` calculate invoice revenue with
  different syntax, while `work_order_service.py` and `domain/policies.py`
  independently calculate priority-based service dates; these are semantic
  duplication candidates.
- `application/services/operations_facade.py` is an intentionally oversized
  API-aware orchestration boundary that constructs every service and exposes
  several response models. It is an architectural refactoring hotspot.
- Asset lifecycle, contract management, and notification delivery each have
  separate domain, DTO, mapper, repository, service, schema, and router files.
  Their repeated search, entity lookup, due-date, serialization, and status
  handling logic is intentionally distributed across layers to mimic a growing
  production codebase.
- The fixture retains intentional `TYPE_CHECKING` dependency cycles for
  architecture testing: domain models point back to their services and API
  schemas point back to the operations façade. These imports are visible to the
  AST dependency graph but do not execute at runtime. The former infrastructure
  cycle was removed: the repository aggregate composes focused repositories,
  while focused repository modules are prevented by a regression test from
  importing the aggregate in return.
- `application/services/operational_control_tower.py` and
  `infrastructure/legacy_operations_exporter.py` are intentionally high-risk
  refactoring targets: they combine customer, work-order, inventory, asset,
  contract, invoice, technician, and notification data with nested loops,
  deeply branched scoring, repeated grouping, and overlapping export logic.
  The dispatch-planning feature adds SLA breach detection, customer risk tiers,
  technician capacity forecasting, contract coverage, stock blockers, backlog
  ranking, and a separately evolved legacy partner manifest. Its repeated SLA,
  queue, normalization, and cost helpers intentionally provide exact duplicate
  blocks alongside the semantic duplication in the two planning paths.
