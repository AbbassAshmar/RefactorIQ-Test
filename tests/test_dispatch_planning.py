from __future__ import annotations

from datetime import date
from decimal import Decimal

from nimbus_ops.application.services.operational_control_tower import (
    _dispatch_estimated_costs,
)
from nimbus_ops.domain.entities import Invoice, InvoiceLine
from nimbus_ops.domain.enums import InvoiceStatus
from nimbus_ops.domain.value_objects import Money


def test_dispatch_costs_remain_partitioned_by_currency() -> None:
    assert _dispatch_estimated_costs(
        "USD",
        380.0,
        [("EUR", 24.5), ("USD", 37.0), ("EUR", 5.5)],
    ) == {
        "USD": 417.0,
        "EUR": 30.0,
    }


def test_invoice_subtotal_preserves_non_default_currency() -> None:
    invoice = Invoice(
        id="inv_eur",
        customer_id="cus_eu",
        work_order_id="wo_eu",
        status=InvoiceStatus.ISSUED,
        issued_on=date(2026, 7, 18),
        due_on=date(2026, 8, 17),
        lines=[
            InvoiceLine("Inspection", 2, Money(Decimal("45.00"), "EUR")),
            InvoiceLine("Travel", 1, Money(Decimal("15.00"), "EUR")),
        ],
    )

    assert invoice.subtotal() == Money(Decimal("105.00"), "EUR")
