from __future__ import annotations

from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.entities import Customer
from nimbus_ops.domain.exceptions import EntityNotFoundError


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


def _sort_named_records(records):
    named_records = [record for record in records if record.name]
    ordered_records = sorted(named_records, key=lambda record: record.name.casefold())
    return [record for record in ordered_records]


def _customer_matches_query(customer: Customer, query: str) -> bool:
    needle = query.strip().casefold()
    searchable = f"{customer.name} {customer.email} {' '.join(customer.tags)}".casefold()
    return needle in searchable


class CustomerService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("customer service")

    def list_customers(self, query: str | None = None) -> list[Customer]:
        with self.uow as uow:
            customers = _sort_named_records(uow.customers.list())
            return [customer for customer in customers if not query or _customer_matches_query(customer, query)]

    def get_customer(self, customer_id: str) -> Customer:
        with self.uow as uow:
            customer = uow.customers.get(customer_id)
            return _require_entity(customer, "Customer", customer_id)
