from __future__ import annotations


class DomainError(Exception):
    """Base exception for business rule failures."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(f"{entity_name} '{entity_id}' was not found.")
        self.entity_name = entity_name
        self.entity_id = entity_id


class CreditHoldError(DomainError):
    pass


class SchedulingError(DomainError):
    pass


class InventoryReservationError(DomainError):
    pass
