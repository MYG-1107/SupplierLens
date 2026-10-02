from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    gstin TEXT,
    website TEXT,
    registered_address TEXT,
    bank_account_name TEXT,
    category TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'not_verified',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_verified_at TEXT
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    document_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    extracted_fields TEXT NOT NULL DEFAULT '{}',
    extraction_method TEXT NOT NULL DEFAULT 'metadata',
    text_excerpt TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sqlite_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:////"):
        return url.removeprefix("sqlite:////")
    if url.startswith("sqlite:///"):
        return url.removeprefix("sqlite:///")
    return "/data/supplierlens.db"


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    path = _sqlite_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def add_audit(supplier_id: int | None, event_type: str, message: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_events (supplier_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
            (supplier_id, event_type, message, utc_now()),
        )


def seed_demo() -> None:
    with get_conn() as conn:
        exists = conn.execute("SELECT COUNT(*) AS c FROM suppliers").fetchone()["c"]
        if exists:
            return
        now = utc_now()
        suppliers = [
            ("ABC Components Private Limited", "36ABCDE1234F1Z5", "https://example.com", "Plot 12, Industrial Area, Hyderabad, Telangana", "ABC Components Private Limited", "Industrial components", "Demo supplier with consistent evidence", "verified_with_limits"),
            ("Northstar Tools & Fasteners", "36ABC1234DE5FZ7", "https://northstar.example", "Warehouse 4, Jeedimetla, Hyderabad, Telangana", "Northstar Tools", "Industrial supplies", "Demo supplier with an intentional bank-name mismatch", "review"),
            ("BluePeak Electricals", None, None, "Survey 18, Kukatpally, Hyderabad", "BluePeak Electricals", "Electrical supplies", "Demo supplier with missing registration evidence", "attention"),
        ]
        for s in suppliers:
            cur = conn.execute(
                """INSERT INTO suppliers
                (supplier_name, gstin, website, registered_address, bank_account_name, category, notes, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*s, now, now),
            )
            sid = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO audit_events (supplier_id, event_type, message, created_at) VALUES (?, ?, ?, ?)",
                (sid, "supplier.created", "Demo supplier seeded", now),
            )
