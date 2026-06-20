from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DomainEvent:
    name: str
    aggregate_id: str
    payload: dict[str, object]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def work_order_created(work_order_id: str, customer_id: str, priority: str) -> DomainEvent:
    return DomainEvent(
        name="work_order.created",
        aggregate_id=work_order_id,
        payload={"customer_id": customer_id, "priority": priority},
    )


def work_order_completed(work_order_id: str, customer_id: str) -> DomainEvent:
    return DomainEvent(
        name="work_order.completed",
        aggregate_id=work_order_id,
        payload={"customer_id": customer_id},
    )


def invoice_issued(invoice_id: str, customer_id: str, total: str) -> DomainEvent:
    return DomainEvent(
        name="invoice.issued",
        aggregate_id=invoice_id,
        payload={"customer_id": customer_id, "total": total},
    )
