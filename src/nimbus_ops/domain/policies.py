from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from nimbus_ops.domain.entities import Customer, InventoryItem, RequiredPart, Technician, WorkOrder
from nimbus_ops.domain.enums import CustomerStatus, WorkOrderPriority
from nimbus_ops.domain.exceptions import CreditHoldError, InventoryReservationError, SchedulingError
from nimbus_ops.domain.value_objects import Money


class WorkOrderPolicy:
    def validate_customer_can_request(self, customer: Customer, work_order: WorkOrder) -> None:
        estimate = work_order.estimated_labor_total()
        if work_order.priority == WorkOrderPriority.EMERGENCY:
            estimate = estimate.add(Money(Decimal("150.00")))
        if customer.status == CustomerStatus.DELINQUENT:
            raise CreditHoldError("Delinquent customers cannot create new work orders.")
        if not customer.can_accept_new_work(estimate):
            raise CreditHoldError("Customer credit limit would be exceeded.")

    def target_service_date(self, requested_date: date, priority: WorkOrderPriority) -> date:
        if priority == WorkOrderPriority.EMERGENCY:
            return requested_date
        if priority == WorkOrderPriority.HIGH:
            return requested_date + timedelta(days=1)
        if priority == WorkOrderPriority.NORMAL:
            return requested_date + timedelta(days=3)
        return requested_date + timedelta(days=7)

    def required_response_hours(self, priority: WorkOrderPriority, has_safety_skill: bool) -> int:
        if priority == WorkOrderPriority.EMERGENCY and has_safety_skill:
            return 2
        if priority == WorkOrderPriority.EMERGENCY:
            return 4
        if priority == WorkOrderPriority.HIGH and has_safety_skill:
            return 8
        if priority == WorkOrderPriority.HIGH:
            return 12
        if priority == WorkOrderPriority.NORMAL:
            return 48
        return 96


class InventoryPolicy:
    def validate_parts_available(self, parts: list[RequiredPart], inventory: dict[str, InventoryItem]) -> None:
        missing: list[str] = []
        short: list[str] = []
        inactive: list[str] = []

        for part in parts:
            item = inventory.get(part.sku)
            if item is None:
                missing.append(part.sku)
                continue
            if not item.active:
                inactive.append(part.sku)
            elif item.quantity_on_hand < part.quantity:
                short.append(f"{part.sku} needs {part.quantity}, has {item.quantity_on_hand}")

        if missing or short or inactive:
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if short:
                details.append(f"short: {', '.join(short)}")
            if inactive:
                details.append(f"inactive: {', '.join(inactive)}")
            raise InventoryReservationError("; ".join(details))


class SchedulingPolicy:
    def choose_technician(
        self,
        work_order: WorkOrder,
        technicians: list[Technician],
        unavailable_technician_ids: set[str],
    ) -> Technician:
        candidates: list[tuple[int, Technician]] = []
        for technician in technicians:
            if technician.id in unavailable_technician_ids:
                continue
            if not technician.can_handle(work_order.required_skills, work_order.estimated_hours):
                continue

            score = 0
            if work_order.priority in {WorkOrderPriority.HIGH, WorkOrderPriority.EMERGENCY}:
                score += 20
            score += len(technician.skills.intersection(work_order.required_skills)) * 10
            score += max(technician.daily_capacity_hours - work_order.estimated_hours, 0)
            if technician.daily_capacity_hours >= 10:
                score += 3
            candidates.append((score, technician))

        if not candidates:
            raise SchedulingError("No eligible technician is available for this work order.")

        candidates.sort(key=lambda candidate: (-candidate[0], candidate[1].name))
        return candidates[0][1]
