from __future__ import annotations

from nimbus_ops.application.asset_dto import AssetSummary
from nimbus_ops.domain.assets import Asset


def to_asset_summary(asset: Asset) -> AssetSummary:
    return AssetSummary(
        id=asset.id,
        customer_id=asset.customer_id,
        name=asset.name,
        serial_number=asset.serial_number,
        category=asset.category,
        installed_on=asset.installed_on,
        service_due_on=asset.service_due_on(),
        status=asset.status,
        site_address=asset.site_address,
    )

