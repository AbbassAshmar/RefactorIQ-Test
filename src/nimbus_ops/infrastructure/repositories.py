from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from nimbus_ops.application.ports import UnitOfWork
from nimbus_ops.infrastructure.asset_repository import SQLiteAssetRepository
from nimbus_ops.infrastructure.contract_repository import SQLiteContractRepository
from nimbus_ops.domain.entities import (
    Customer,
    InventoryItem,
    Invoice,
    InvoiceLine,
    RequiredPart,
    Technician,
    WorkOrder,
)
from nimbus_ops.domain.enums import (
    CustomerStatus,
    InvoiceStatus,
    TechnicianSkill,
    WorkOrderPriority,
    WorkOrderStatus,
)
from nimbus_ops.domain.events import DomainEvent
from nimbus_ops.domain.value_objects import Address, Money
from nimbus_ops.infrastructure.database import connect
from nimbus_ops.infrastructure.notification_repository import SQLiteNotificationRepository


def _json_list(value: str | None) -> list[object]:
    if not value:
        return []
    loaded = json.loads(value)
    return loaded if isinstance(loaded, list) else []


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class SQLiteCustomerRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, customer_id: str) -> Customer | None:
        row = self.connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self) -> list[Customer]:
        rows = self.connection.execute("SELECT * FROM customers ORDER BY name").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, customer: Customer) -> None:
        self.connection.execute(
            """
            INSERT INTO customers (
                id, name, email, status, credit_limit_amount,
                outstanding_balance_amount, currency, tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                status = excluded.status,
                credit_limit_amount = excluded.credit_limit_amount,
                outstanding_balance_amount = excluded.outstanding_balance_amount,
                currency = excluded.currency,
                tags = excluded.tags
            """,
            (
                customer.id,
                customer.name,
                customer.email,
                customer.status.value,
                str(customer.credit_limit.amount),
                str(customer.outstanding_balance.amount),
                customer.credit_limit.currency,
                json.dumps(customer.tags),
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> Customer:
        return Customer(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            status=CustomerStatus(row["status"]),
            credit_limit=Money(Decimal(row["credit_limit_amount"]), row["currency"]),
            outstanding_balance=Money(Decimal(row["outstanding_balance_amount"]), row["currency"]),
            tags=[str(tag) for tag in _json_list(row["tags"])],
        )


class SQLiteTechnicianRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list(self) -> list[Technician]:
        rows = self.connection.execute("SELECT * FROM technicians ORDER BY name").fetchall()
        return [
            Technician(
                id=row["id"],
                name=row["name"],
                skills={TechnicianSkill(skill) for skill in _json_list(row["skills"])},
                daily_capacity_hours=row["daily_capacity_hours"],
                active=bool(row["active"]),
            )
            for row in rows
        ]

    def save(self, technician: Technician) -> None:
        self.connection.execute(
            """
            INSERT INTO technicians (id, name, skills, daily_capacity_hours, active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                skills = excluded.skills,
                daily_capacity_hours = excluded.daily_capacity_hours,
                active = excluded.active
            """,
            (
                technician.id,
                technician.name,
                json.dumps(sorted(skill.value for skill in technician.skills)),
                technician.daily_capacity_hours,
                int(technician.active),
            ),
        )


class SQLiteInventoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_many(self, skus: list[str]) -> dict[str, InventoryItem]:
        if not skus:
            return {}
        placeholders = ",".join("?" for _ in skus)
        rows = self.connection.execute(
            f"SELECT * FROM inventory_items WHERE sku IN ({placeholders})",
            tuple(skus),
        ).fetchall()
        return {row["sku"]: self._to_entity(row) for row in rows}

    def list(self) -> list[InventoryItem]:
        rows = self.connection.execute("SELECT * FROM inventory_items ORDER BY sku").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, item: InventoryItem) -> None:
        self.connection.execute(
            """
            INSERT INTO inventory_items (
                sku, name, quantity_on_hand, reorder_point,
                unit_cost_amount, currency, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                name = excluded.name,
                quantity_on_hand = excluded.quantity_on_hand,
                reorder_point = excluded.reorder_point,
                unit_cost_amount = excluded.unit_cost_amount,
                currency = excluded.currency,
                active = excluded.active
            """,
            (
                item.sku,
                item.name,
                item.quantity_on_hand,
                item.reorder_point,
                str(item.unit_cost.amount),
                item.unit_cost.currency,
                int(item.active),
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> InventoryItem:
        return InventoryItem(
            sku=row["sku"],
            name=row["name"],
            quantity_on_hand=row["quantity_on_hand"],
            reorder_point=row["reorder_point"],
            unit_cost=Money(Decimal(row["unit_cost_amount"]), row["currency"]),
            active=bool(row["active"]),
        )


class SQLiteWorkOrderRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, work_order_id: str) -> WorkOrder | None:
        row = self.connection.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self, status: str | None = None) -> list[WorkOrder]:
        if status:
            rows = self.connection.execute(
                "SELECT * FROM work_orders WHERE status = ? ORDER BY requested_date DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM work_orders ORDER BY requested_date DESC").fetchall()
        return [self._to_entity(row) for row in rows]

    def list_for_date(self, scheduled_date: date) -> list[WorkOrder]:
        rows = self.connection.execute(
            "SELECT * FROM work_orders WHERE scheduled_date = ?",
            (scheduled_date.isoformat(),),
        ).fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, work_order: WorkOrder) -> None:
        self.connection.execute(
            """
            INSERT INTO work_orders (
                id, customer_id, title, description, priority, status, requested_date,
                address_line1, address_line2, city, country, postal_code, required_parts,
                required_skills, estimated_hours, assigned_technician_id, scheduled_date,
                completed_at, labor_rate_amount, currency, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                priority = excluded.priority,
                status = excluded.status,
                required_parts = excluded.required_parts,
                required_skills = excluded.required_skills,
                estimated_hours = excluded.estimated_hours,
                assigned_technician_id = excluded.assigned_technician_id,
                scheduled_date = excluded.scheduled_date,
                completed_at = excluded.completed_at,
                labor_rate_amount = excluded.labor_rate_amount,
                notes = excluded.notes
            """,
            (
                work_order.id,
                work_order.customer_id,
                work_order.title,
                work_order.description,
                work_order.priority.value,
                work_order.status.value,
                work_order.requested_date.isoformat(),
                work_order.site_address.line1,
                work_order.site_address.line2,
                work_order.site_address.city,
                work_order.site_address.country,
                work_order.site_address.postal_code,
                json.dumps([part.__dict__ for part in work_order.required_parts]),
                json.dumps(sorted(skill.value for skill in work_order.required_skills)),
                work_order.estimated_hours,
                work_order.assigned_technician_id,
                work_order.scheduled_date.isoformat() if work_order.scheduled_date else None,
                work_order.completed_at.isoformat() if work_order.completed_at else None,
                str(work_order.labor_rate.amount),
                work_order.labor_rate.currency,
                json.dumps(work_order.notes),
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> WorkOrder:
        parts = [RequiredPart(sku=str(part["sku"]), quantity=int(part["quantity"])) for part in _json_list(row["required_parts"])]
        return WorkOrder(
            id=row["id"],
            customer_id=row["customer_id"],
            title=row["title"],
            description=row["description"],
            priority=WorkOrderPriority(row["priority"]),
            status=WorkOrderStatus(row["status"]),
            requested_date=date.fromisoformat(row["requested_date"]),
            site_address=Address(
                line1=row["address_line1"],
                line2=row["address_line2"],
                city=row["city"],
                country=row["country"],
                postal_code=row["postal_code"],
            ),
            required_parts=parts,
            required_skills={TechnicianSkill(skill) for skill in _json_list(row["required_skills"])},
            estimated_hours=row["estimated_hours"],
            assigned_technician_id=row["assigned_technician_id"],
            scheduled_date=_date(row["scheduled_date"]),
            completed_at=_datetime(row["completed_at"]),
            labor_rate=Money(Decimal(row["labor_rate_amount"]), row["currency"]),
            notes=[str(note) for note in _json_list(row["notes"])],
        )


class SQLiteInvoiceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, invoice_id: str) -> Invoice | None:
        row = self.connection.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return self._to_entity(row) if row else None

    def list(self) -> list[Invoice]:
        rows = self.connection.execute("SELECT * FROM invoices ORDER BY issued_on DESC").fetchall()
        return [self._to_entity(row) for row in rows]

    def save(self, invoice: Invoice) -> None:
        self.connection.execute(
            """
            INSERT INTO invoices (id, customer_id, work_order_id, status, issued_on, due_on, lines)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                issued_on = excluded.issued_on,
                due_on = excluded.due_on,
                lines = excluded.lines
            """,
            (
                invoice.id,
                invoice.customer_id,
                invoice.work_order_id,
                invoice.status.value,
                invoice.issued_on.isoformat() if invoice.issued_on else None,
                invoice.due_on.isoformat() if invoice.due_on else None,
                json.dumps(
                    [
                        {
                            "description": line.description,
                            "quantity": line.quantity,
                            "unit_price": str(line.unit_price.amount),
                            "currency": line.unit_price.currency,
                        }
                        for line in invoice.lines
                    ]
                ),
            ),
        )

    def _to_entity(self, row: sqlite3.Row) -> Invoice:
        lines = [
            InvoiceLine(
                description=str(line["description"]),
                quantity=int(line["quantity"]),
                unit_price=Money(Decimal(str(line["unit_price"])), str(line["currency"])),
            )
            for line in _json_list(row["lines"])
        ]
        return Invoice(
            id=row["id"],
            customer_id=row["customer_id"],
            work_order_id=row["work_order_id"],
            status=InvoiceStatus(row["status"]),
            issued_on=_date(row["issued_on"]),
            due_on=_date(row["due_on"]),
            lines=lines,
        )


class SQLiteEventPublisher:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def publish(self, event: DomainEvent) -> None:
        self.connection.execute(
            """
            INSERT INTO outbox_events (name, aggregate_id, payload, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                event.name,
                event.aggregate_id,
                json.dumps(event.payload, sort_keys=True),
                event.occurred_at.isoformat(),
            ),
        )


class SQLiteUnitOfWork(UnitOfWork):
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> "SQLiteUnitOfWork":
        self.connection = connect(self.database_path)
        self.customers = SQLiteCustomerRepository(self.connection)
        self.work_orders = SQLiteWorkOrderRepository(self.connection)
        self.inventory = SQLiteInventoryRepository(self.connection)
        self.technicians = SQLiteTechnicianRepository(self.connection)
        self.invoices = SQLiteInvoiceRepository(self.connection)
        self.assets = SQLiteAssetRepository(self.connection)
        self.contracts = SQLiteContractRepository(self.connection)
        self.notifications = SQLiteNotificationRepository(self.connection)
        self.events = SQLiteEventPublisher(self.connection)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.connection is None:
            return
        if exc_type:
            self.connection.rollback()
        self.connection.close()
        self.connection = None

    def commit(self) -> None:
        if self.connection is None:
            raise RuntimeError("Cannot commit outside an active unit of work.")
        self.connection.commit()
