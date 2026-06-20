from __future__ import annotations

from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.domain.entities import Customer
from nimbus_ops.domain.exceptions import EntityNotFoundError


class CustomerService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list_customers(self) -> list[Customer]:
        with self.uow as uow:
            return uow.customers.list()

    def get_customer(self, customer_id: str) -> Customer:
        with self.uow as uow:
            customer = uow.customers.get(customer_id)
            if customer is None:
                raise EntityNotFoundError("Customer", customer_id)
            return customer
