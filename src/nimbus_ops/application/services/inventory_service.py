from __future__ import annotations

from nimbus_ops.application.dto import InventoryHealth
from nimbus_ops.application.mappers import to_inventory_health
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.exceptions import EntityNotFoundError


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


def _sort_named_records(records):
    named_records = [record for record in records if record.name]
    ordered_records = sorted(named_records, key=lambda record: record.name.casefold())
    return [record for record in ordered_records]


class InventoryService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("inventory service")

    def list_inventory_health(self) -> list[InventoryHealth]:
        with self.uow as uow:
            return [to_inventory_health(item) for item in _sort_named_records(uow.inventory.list())]

    def adjust_stock(self, sku: str, delta: int) -> InventoryHealth:
        with self.uow as uow:
            items = uow.inventory.get_many([sku])
            item = items.get(sku)
            item = _require_entity(item, "InventoryItem", sku)
            if item.quantity_on_hand + delta < 0:
                raise ValueError("Stock adjustment would make quantity negative.")
            item.quantity_on_hand += delta
            uow.inventory.save(item)
            uow.commit()
            return to_inventory_health(item)
