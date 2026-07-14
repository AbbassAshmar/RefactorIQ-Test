from __future__ import annotations

from datetime import date

from nimbus_ops.application.contract_dto import ContractSummary
from nimbus_ops.domain.contracts import ServiceContract


def to_contract_summary(contract: ServiceContract, as_of: date) -> ContractSummary:
    return ContractSummary(
        id=contract.id,
        customer_id=contract.customer_id,
        name=contract.name,
        tier=contract.tier,
        status=contract.status,
        starts_on=contract.starts_on,
        ends_on=contract.ends_on,
        monthly_limit=contract.monthly_limit.amount,
        currency=contract.monthly_limit.currency,
        included_hours=contract.included_hours,
        days_remaining=contract.days_remaining(as_of),
    )

