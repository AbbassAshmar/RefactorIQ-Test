from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from nimbus_ops.domain.entities import Customer, InventoryItem, RequiredPart, Technician, WorkOrder
from nimbus_ops.domain.enums import CustomerStatus, TechnicianSkill, WorkOrderPriority, WorkOrderStatus
from nimbus_ops.domain.exceptions import CreditHoldError, InventoryReservationError, SchedulingError
from nimbus_ops.domain.policies import InventoryPolicy, SchedulingPolicy, WorkOrderPolicy
from nimbus_ops.domain.value_objects import Address, Money


def test_money_and_address_validation_paths() -> None:
    total = Money.from_float(10.125).add(Money(Decimal("2.10")))
    address = Address(line1="  42 Industrial Way  ", city=" Beirut ", country="LB", postal_code="1107")

    assert total.amount == Decimal("12.23")
    assert address.normalized() == "42 Industrial Way, Beirut, 1107, LB"
    with pytest.raises(ValueError, match="different currencies"):
        Money(Decimal("1.00"), "USD").add(Money(Decimal("1.00"), "EUR"))
    with pytest.raises(ValueError, match="negative"):
        Money(Decimal("-1.00"))


def test_work_order_policy_credit_hold_and_response_windows() -> None:
    policy = WorkOrderPolicy()
    work_order = _work_order(priority=WorkOrderPriority.EMERGENCY, estimated_hours=2)
    delinquent = Customer(
        id="cus_bad",
        name="Bad Credit LLC",
        email="bad@example.test",
        status=CustomerStatus.DELINQUENT,
    )

    with pytest.raises(CreditHoldError):
        policy.validate_customer_can_request(delinquent, work_order)

    assert policy.target_service_date(date(2026, 6, 20), WorkOrderPriority.LOW) == date(2026, 6, 27)
    assert policy.required_response_hours(WorkOrderPriority.EMERGENCY, has_safety_skill=True) == 2
    assert policy.required_response_hours(WorkOrderPriority.HIGH, has_safety_skill=False) == 12


def test_inventory_policy_reports_missing_short_and_inactive_parts() -> None:
    inventory = {
        "FILTER-10": InventoryItem("FILTER-10", "Filter", 1, 5, Money(Decimal("18.50"))),
        "PUMP-01": InventoryItem("PUMP-01", "Pump", 10, 2, Money(Decimal("95.00")), active=False),
    }

    with pytest.raises(InventoryReservationError) as exc:
        InventoryPolicy().validate_parts_available(
            [
                RequiredPart("UNKNOWN", 1),
                RequiredPart("FILTER-10", 2),
                RequiredPart("PUMP-01", 1),
            ],
            inventory,
        )

    message = str(exc.value)
    assert "missing: UNKNOWN" in message
    assert "short: FILTER-10 needs 2, has 1" in message
    assert "inactive: PUMP-01" in message


def test_scheduling_policy_prefers_best_available_technician() -> None:
    work_order = _work_order(
        priority=WorkOrderPriority.HIGH,
        required_skills={TechnicianSkill.ELECTRICAL, TechnicianSkill.SAFETY},
        estimated_hours=4,
    )
    technicians = [
        Technician("tech_omar", "Omar", {TechnicianSkill.ELECTRICAL}, daily_capacity_hours=8),
        Technician(
            "tech_maya",
            "Maya",
            {TechnicianSkill.ELECTRICAL, TechnicianSkill.SAFETY, TechnicianSkill.NETWORKING},
            daily_capacity_hours=10,
        ),
    ]

    chosen = SchedulingPolicy().choose_technician(work_order, technicians, unavailable_technician_ids=set())

    assert chosen.id == "tech_maya"
    with pytest.raises(SchedulingError):
        SchedulingPolicy().choose_technician(work_order, technicians, unavailable_technician_ids={"tech_maya"})


def _work_order(
    priority: WorkOrderPriority = WorkOrderPriority.NORMAL,
    required_skills: set[TechnicianSkill] | None = None,
    estimated_hours: int = 2,
) -> WorkOrder:
    return WorkOrder(
        id="wo_test",
        customer_id="cus_acme",
        title="Inspect generator",
        description="Inspect generator and breaker panel.",
        priority=priority,
        status=WorkOrderStatus.READY,
        requested_date=date(2026, 6, 20),
        site_address=Address("42 Industrial Way", "Beirut", "LB", "1107"),
        required_skills=required_skills or {TechnicianSkill.ELECTRICAL},
        estimated_hours=estimated_hours,
    )
