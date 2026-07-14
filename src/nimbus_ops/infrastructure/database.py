from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL,
    credit_limit_amount TEXT NOT NULL,
    outstanding_balance_amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    tags TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS technicians (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    skills TEXT NOT NULL,
    daily_capacity_hours INTEGER NOT NULL,
    active INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_items (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity_on_hand INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    unit_cost_amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    active INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS work_orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_date TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    required_parts TEXT NOT NULL,
    required_skills TEXT NOT NULL,
    estimated_hours INTEGER NOT NULL,
    assigned_technician_id TEXT,
    scheduled_date TEXT,
    completed_at TEXT,
    labor_rate_amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    work_order_id TEXT NOT NULL,
    status TEXT NOT NULL,
    issued_on TEXT,
    due_on TEXT,
    lines TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    installed_on TEXT NOT NULL,
    last_service_date TEXT,
    service_interval_days INTEGER NOT NULL,
    status TEXT NOT NULL,
    site_address TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_contracts (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    tier TEXT NOT NULL,
    status TEXT NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    monthly_limit_amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    included_hours INTEGER NOT NULL,
    auto_renew INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    sent_at TEXT
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
