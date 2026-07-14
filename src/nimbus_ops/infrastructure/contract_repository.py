from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from nimbus_ops.domain.contracts import ServiceContract
from nimbus_ops.domain.enums import ContractStatus, ContractTier
from nimbus_ops.domain.value_objects import Money


class SQLiteContractRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, contract_id: str) -> ServiceContract | None:
        row = self.connection.execute("SELECT * FROM service_contracts WHERE id = ?", (contract_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self, customer_id: str | None = None) -> list[ServiceContract]:
        if customer_id:
            rows = self.connection.execute(
                "SELECT * FROM service_contracts WHERE customer_id = ? ORDER BY ends_on",
                (customer_id,),
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM service_contracts ORDER BY ends_on").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, contract: ServiceContract) -> None:
        self.connection.execute(
            """
            INSERT INTO service_contracts (
                id, customer_id, name, tier, status, starts_on, ends_on,
                monthly_limit_amount, currency, included_hours, auto_renew
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                tier = excluded.tier,
                status = excluded.status,
                ends_on = excluded.ends_on,
                monthly_limit_amount = excluded.monthly_limit_amount,
                included_hours = excluded.included_hours,
                auto_renew = excluded.auto_renew
            """,
            (
                contract.id,
                contract.customer_id,
                contract.name,
                contract.tier.value,
                contract.status.value,
                contract.starts_on.isoformat(),
                contract.ends_on.isoformat(),
                str(contract.monthly_limit.amount),
                contract.monthly_limit.currency,
                contract.included_hours,
                int(contract.auto_renew),
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> ServiceContract:
        return ServiceContract(
            id=row["id"],
            customer_id=row["customer_id"],
            name=row["name"],
            tier=ContractTier(row["tier"]),
            status=ContractStatus(row["status"]),
            starts_on=date.fromisoformat(row["starts_on"]),
            ends_on=date.fromisoformat(row["ends_on"]),
            monthly_limit=Money(Decimal(row["monthly_limit_amount"]), row["currency"]),
            included_hours=row["included_hours"],
            auto_renew=bool(row["auto_renew"]),
        )

