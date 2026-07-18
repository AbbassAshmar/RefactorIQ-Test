from __future__ import annotations

import sqlite3
from datetime import date

from nimbus_ops.domain.assets import Asset
from nimbus_ops.domain.enums import AssetStatus


class SQLiteAssetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, asset_id: str) -> Asset | None:
        row = self.connection.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self, customer_id: str | None = None) -> list[Asset]:
        if customer_id:
            rows = self.connection.execute(
                "SELECT * FROM assets WHERE customer_id = ? ORDER BY name",
                (customer_id,),
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM assets ORDER BY name").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, asset: Asset) -> None:
        self.connection.execute(
            """
            INSERT INTO assets (
                id, customer_id, name, serial_number, category, installed_on,
                last_service_date, service_interval_days, status, site_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                last_service_date = excluded.last_service_date,
                service_interval_days = excluded.service_interval_days,
                status = excluded.status,
                site_address = excluded.site_address
            """,
            (
                asset.id,
                asset.customer_id,
                asset.name,
                asset.serial_number,
                asset.category,
                asset.installed_on.isoformat(),
                asset.last_service_date.isoformat() if asset.last_service_date else None,
                asset.service_interval_days,
                asset.status.value,
                asset.site_address,
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> Asset:
        return Asset(
            id=row["id"],
            customer_id=row["customer_id"],
            name=row["name"],
            serial_number=row["serial_number"],
            category=row["category"],
            installed_on=date.fromisoformat(row["installed_on"]),
            last_service_date=(
                date.fromisoformat(row["last_service_date"])
                if row["last_service_date"]
                else None
            ),
            service_interval_days=row["service_interval_days"],
            status=AssetStatus(row["status"]),
            site_address=row["site_address"],
        )
