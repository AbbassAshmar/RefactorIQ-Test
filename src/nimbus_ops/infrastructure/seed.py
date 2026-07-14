from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from nimbus_ops.domain.assets import Asset
from nimbus_ops.domain.contracts import ServiceContract
from nimbus_ops.domain.entities import Customer, InventoryItem, Technician
from nimbus_ops.domain.enums import AssetStatus, ContractStatus, ContractTier, CustomerStatus, TechnicianSkill
from nimbus_ops.domain.value_objects import Money
from nimbus_ops.infrastructure.database import initialize_database
from nimbus_ops.infrastructure.repositories import SQLiteUnitOfWork


def seed_database(database_path: Path) -> None:
    initialize_database(database_path)
    with SQLiteUnitOfWork(database_path) as uow:
        if uow.customers.list():
            return
        customers = [
            Customer(
                id="cus_acme",
                name="Acme Facilities",
                email="ops@acme.example",
                status=CustomerStatus.ACTIVE,
                credit_limit=Money(Decimal("12000.00")),
                tags=["enterprise", "generator"],
            ),
            Customer(
                id="cus_levant",
                name="Levant Clinics",
                email="facilities@levant.example",
                status=CustomerStatus.ACTIVE,
                credit_limit=Money(Decimal("8500.00")),
                tags=["healthcare", "priority"],
            ),
        ]
        technicians = [
            Technician(
                id="tech_maya",
                name="Maya Haddad",
                skills={TechnicianSkill.ELECTRICAL, TechnicianSkill.SAFETY, TechnicianSkill.NETWORKING},
                daily_capacity_hours=10,
            ),
            Technician(
                id="tech_omar",
                name="Omar Saleh",
                skills={TechnicianSkill.HVAC, TechnicianSkill.PLUMBING, TechnicianSkill.SAFETY},
                daily_capacity_hours=8,
            ),
        ]
        inventory = [
            InventoryItem(
                sku="FILTER-10",
                name="Generator oil filter",
                quantity_on_hand=32,
                reorder_point=10,
                unit_cost=Money(Decimal("18.50")),
            ),
            InventoryItem(
                sku="BREAKER-20",
                name="20A industrial breaker",
                quantity_on_hand=8,
                reorder_point=6,
                unit_cost=Money(Decimal("42.00")),
            ),
            InventoryItem(
                sku="THERMO-01",
                name="Smart thermostat",
                quantity_on_hand=5,
                reorder_point=5,
                unit_cost=Money(Decimal("67.25")),
            ),
        ]
        assets = [
            Asset(
                id="asset_acme_generator",
                customer_id="cus_acme",
                name="Main generator",
                serial_number="GEN-ACME-001",
                category="generator",
                installed_on=date(2024, 1, 15),
                last_service_date=date(2025, 12, 1),
                service_interval_days=180,
                status=AssetStatus.ACTIVE,
                site_address="42 Industrial Way, Beirut",
            ),
            Asset(
                id="asset_levant_hvac",
                customer_id="cus_levant",
                name="Clinic HVAC unit",
                serial_number="HVAC-LEV-009",
                category="hvac",
                installed_on=date(2026, 2, 20),
                service_interval_days=180,
                status=AssetStatus.ACTIVE,
                site_address="18 Hamra Street, Beirut",
            ),
        ]
        contracts = [
            ServiceContract(
                id="contract_acme_priority",
                customer_id="cus_acme",
                name="Acme Priority Care",
                tier=ContractTier.PRIORITY,
                status=ContractStatus.ACTIVE,
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 12, 31),
                monthly_limit=Money(Decimal("2500.00")),
                included_hours=40,
                auto_renew=True,
            ),
            ServiceContract(
                id="contract_levant_basic",
                customer_id="cus_levant",
                name="Clinic Equipment Cover",
                tier=ContractTier.BASIC,
                status=ContractStatus.ACTIVE,
                starts_on=date(2026, 3, 1),
                ends_on=date(2026, 8, 15),
                monthly_limit=Money(Decimal("1200.00")),
                included_hours=16,
                auto_renew=False,
            ),
        ]
        for customer in customers:
            uow.customers.save(customer)
        for technician in technicians:
            uow.technicians.save(technician)
        for item in inventory:
            uow.inventory.save(item)
        for asset in assets:
            uow.assets.save(asset)
        for contract in contracts:
            uow.contracts.save(contract)
        uow.commit()
