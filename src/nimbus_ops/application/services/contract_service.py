from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from nimbus_ops.application.contract_dto import ContractSummary, CreateContractCommand
from nimbus_ops.application.contract_mappers import to_contract_summary
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.contracts import ServiceContract
from nimbus_ops.domain.entities import new_id
from nimbus_ops.domain.enums import ContractStatus
from nimbus_ops.domain.exceptions import EntityNotFoundError
from nimbus_ops.domain.value_objects import Money


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


def _contract_matches_query(contract: ServiceContract, query: str) -> bool:
    needle = query.strip().lower()
    fields = (contract.name, contract.tier.value, contract.customer_id, contract.status.value)
    return any(needle in field.lower() for field in fields)


class ContractService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("contract service")

    def list_contracts(
        self,
        customer_id: str | None = None,
        query: str | None = None,
        as_of: date | None = None,
    ) -> list[ContractSummary]:
        evaluation_date = as_of or date.today()
        with self.uow as uow:
            contracts = uow.contracts.list(customer_id)
            if query:
                contracts = [contract for contract in contracts if _contract_matches_query(contract, query)]
            return [to_contract_summary(contract, evaluation_date) for contract in contracts]

    def get_contract(self, contract_id: str, as_of: date | None = None) -> ContractSummary:
        with self.uow as uow:
            contract = _require_entity(uow.contracts.get(contract_id), "ServiceContract", contract_id)
            return to_contract_summary(contract, as_of or date.today())

    def create_contract(self, command: CreateContractCommand) -> ContractSummary:
        if command.ends_on < command.starts_on:
            raise ValueError("Contract end date must be after its start date.")
        with self.uow as uow:
            customer = _require_entity(uow.customers.get(command.customer_id), "Customer", command.customer_id)
            contract = ServiceContract(
                id=new_id("contract"),
                customer_id=customer.id,
                name=command.name,
                tier=command.tier,
                status=ContractStatus.ACTIVE,
                starts_on=command.starts_on,
                ends_on=command.ends_on,
                monthly_limit=Money(command.monthly_limit),
                included_hours=command.included_hours,
                auto_renew=command.auto_renew,
            )
            uow.contracts.save(contract)
            uow.commit()
            return to_contract_summary(contract, date.today())

    def is_covered(self, contract_id: str, service_date: date) -> bool:
        with self.uow as uow:
            contract = _require_entity(uow.contracts.get(contract_id), "ServiceContract", contract_id)
            return contract.covers(service_date)

    def expiring_soon(self, days: int, as_of: date | None = None) -> list[ContractSummary]:
        evaluation_date = as_of or date.today()
        cutoff = evaluation_date + timedelta(days=days)
        with self.uow as uow:
            contracts = [
                contract
                for contract in uow.contracts.list()
                if contract.status == ContractStatus.ACTIVE
                and evaluation_date <= contract.ends_on <= cutoff
            ]
            return [to_contract_summary(contract, evaluation_date) for contract in contracts]
