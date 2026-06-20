from __future__ import annotations

from nimbus_ops.application.dto import InventoryHealth
from nimbus_ops.application.mappers import to_inventory_health
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.domain.exceptions import EntityNotFoundError


class InventoryService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list_inventory_health(self) -> list[InventoryHealth]:
        with self.uow as uow:
            return [to_inventory_health(item) for item in uow.inventory.list()]

    def adjust_stock(self, sku: str, delta: int) -> InventoryHealth:
        with self.uow as uow:
            items = uow.inventory.get_many([sku])
            item = items.get(sku)
            if item is None:
                raise EntityNotFoundError("InventoryItem", sku)
            if item.quantity_on_hand + delta < 0:
                raise ValueError("Stock adjustment would make quantity negative.")
            item.quantity_on_hand += delta
            uow.inventory.save(item)
            uow.commit()
            return to_inventory_health(item)
