from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from nimbus_ops.application.dto import (
    CompleteWorkOrderCommand,
    CreateWorkOrderCommand,
    ScheduleWorkOrderCommand,
    WorkOrderSummary,
)
from nimbus_ops.application.mappers import to_work_order_summary
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.domain.entities import RequiredPart, WorkOrder, new_id
from nimbus_ops.domain.enums import TechnicianSkill, WorkOrderPriority, WorkOrderStatus
from nimbus_ops.domain.events import work_order_completed, work_order_created
from nimbus_ops.domain.exceptions import EntityNotFoundError
from nimbus_ops.domain.policies import InventoryPolicy, SchedulingPolicy, WorkOrderPolicy


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


def _service_delay_days(priority: WorkOrderPriority) -> int:
    delays = {
        "emergency": 0,
        "high": 1,
        "normal": 3,
        "low": 7,
    }
    return delays.get(getattr(priority, "value", priority), 7)


class WorkOrderService:
    def __init__(
        self,
        uow: UnitOfWork,
        work_order_policy: WorkOrderPolicy | None = None,
        inventory_policy: InventoryPolicy | None = None,
        scheduling_policy: SchedulingPolicy | None = None,
    ) -> None:
        self.uow = uow
        self.work_order_policy = work_order_policy or WorkOrderPolicy()
        self.inventory_policy = inventory_policy or InventoryPolicy()
        self.scheduling_policy = scheduling_policy or SchedulingPolicy()

    def create_work_order(self, command: CreateWorkOrderCommand) -> WorkOrderSummary:
        with self.uow as uow:
            customer = uow.customers.get(command.customer_id)
            customer = _require_entity(customer, "Customer", command.customer_id)

            parts = [RequiredPart(sku=part.sku, quantity=part.quantity) for part in command.required_parts]
            required_skills = {TechnicianSkill(skill) for skill in command.required_skills}
            work_order = WorkOrder(
                id=new_id("wo"),
                customer_id=command.customer_id,
                title=command.title,
                description=command.description,
                priority=command.priority,
                status=WorkOrderStatus.DRAFT,
                requested_date=command.requested_date,
                site_address=command.site_address,
                required_parts=parts,
                required_skills=required_skills,
                estimated_hours=command.estimated_hours,
            )

            inventory = uow.inventory.get_many([part.sku for part in parts])
            self.work_order_policy.validate_customer_can_request(customer, work_order)
            self.inventory_policy.validate_parts_available(parts, inventory)

            for part in parts:
                inventory[part.sku].reserve(part.quantity)
                uow.inventory.save(inventory[part.sku])

            work_order.mark_ready()
            uow.work_orders.save(work_order)
            uow.events.publish(work_order_created(work_order.id, customer.id, work_order.priority.value))
            uow.commit()
            return to_work_order_summary(work_order)

    def list_work_orders(self, status: str | None = None) -> list[WorkOrderSummary]:
        with self.uow as uow:
            return [to_work_order_summary(work_order) for work_order in uow.work_orders.list(status)]

    def schedule_work_order(self, command: ScheduleWorkOrderCommand) -> WorkOrderSummary:
        with self.uow as uow:
            work_order = uow.work_orders.get(command.work_order_id)
            work_order = _require_entity(work_order, "WorkOrder", command.work_order_id)

            scheduled_orders = uow.work_orders.list_for_date(command.scheduled_date)
            unavailable = set(command.unavailable_technician_ids)
            for scheduled in scheduled_orders:
                if scheduled.assigned_technician_id:
                    unavailable.add(scheduled.assigned_technician_id)

            technician = self.scheduling_policy.choose_technician(
                work_order=work_order,
                technicians=uow.technicians.list(),
                unavailable_technician_ids=unavailable,
            )
            work_order.schedule(technician.id, command.scheduled_date)
            uow.work_orders.save(work_order)
            uow.commit()
            return to_work_order_summary(work_order)

    def complete_work_order(self, command: CompleteWorkOrderCommand) -> WorkOrderSummary:
        with self.uow as uow:
            work_order = uow.work_orders.get(command.work_order_id)
            work_order = _require_entity(work_order, "WorkOrder", command.work_order_id)
            completed_at = command.completed_at or datetime.now(timezone.utc)
            work_order.complete(completed_at, command.note)
            uow.work_orders.save(work_order)
            uow.events.publish(work_order_completed(work_order.id, work_order.customer_id))
            uow.commit()
            return to_work_order_summary(work_order)

    def projected_service_date(self, requested_date: date, priority: WorkOrderPriority) -> date:
        return requested_date + timedelta(days=_service_delay_days(priority))
