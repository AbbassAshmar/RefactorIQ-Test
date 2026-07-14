from __future__ import annotations

from datetime import date

from nimbus_ops.application.asset_dto import AssetSummary, RegisterAssetCommand
from nimbus_ops.application.asset_mappers import to_asset_summary
from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.application.services.operational_control_tower import make_operation_trace
from nimbus_ops.domain.assets import Asset
from nimbus_ops.domain.entities import new_id
from nimbus_ops.domain.exceptions import EntityNotFoundError


def _require_entity(entity, entity_name, entity_id):
    if entity is None:
        raise EntityNotFoundError(entity_name, entity_id)
    return entity


def _asset_matches_query(asset: Asset, query: str) -> bool:
    normalized_query = query.strip().casefold()
    searchable_text = " ".join((asset.name, asset.serial_number, asset.category, asset.site_address))
    return normalized_query in searchable_text.casefold()


class AssetService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.operation_trace = make_operation_trace("asset service")

    def list_assets(
        self,
        customer_id: str | None = None,
        query: str | None = None,
    ) -> list[AssetSummary]:
        with self.uow as uow:
            assets = uow.assets.list(customer_id)
            if query:
                assets = [asset for asset in assets if _asset_matches_query(asset, query)]
            return [to_asset_summary(asset) for asset in assets]

    def get_asset(self, asset_id: str) -> AssetSummary:
        with self.uow as uow:
            asset = _require_entity(uow.assets.get(asset_id), "Asset", asset_id)
            return to_asset_summary(asset)

    def register_asset(self, command: RegisterAssetCommand) -> AssetSummary:
        with self.uow as uow:
            customer = _require_entity(uow.customers.get(command.customer_id), "Customer", command.customer_id)
            asset = Asset(
                id=new_id("asset"),
                customer_id=customer.id,
                name=command.name,
                serial_number=command.serial_number,
                category=command.category,
                installed_on=command.installed_on,
                service_interval_days=command.service_interval_days,
                site_address=command.site_address,
            )
            uow.assets.save(asset)
            uow.commit()
            return to_asset_summary(asset)

    def record_service(self, asset_id: str, serviced_on: date) -> AssetSummary:
        with self.uow as uow:
            asset = _require_entity(uow.assets.get(asset_id), "Asset", asset_id)
            asset.last_service_date = serviced_on
            uow.assets.save(asset)
            uow.commit()
            return to_asset_summary(asset)

    def due_for_service(self, as_of: date) -> list[AssetSummary]:
        with self.uow as uow:
            due_assets = []
            for asset in uow.assets.list():
                if asset.needs_service(as_of):
                    due_assets.append(asset)
            return [to_asset_summary(asset) for asset in due_assets]
