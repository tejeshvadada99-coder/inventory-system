"""
migrations.py
-------------
Your live Render database already has tables, and SQLAlchemy's
`create_all()` only creates MISSING tables - it never adds new columns to
tables that exist. This file adds the new customer-role columns safely.

Every statement uses `IF NOT EXISTS`, so it is harmless to run on every
startup: the first run upgrades the database, later runs do nothing.
It only runs on PostgreSQL.
"""
from sqlalchemy import text

from app.database import engine

COLUMN_STATEMENTS = [
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_user_id ON customers (user_id)",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS loyalty_points INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE bills ADD COLUMN IF NOT EXISTS points_earned INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE offers ADD COLUMN IF NOT EXISTS members_only BOOLEAN NOT NULL DEFAULT FALSE",
    # The `role` column is a PostgreSQL ENUM type; teach it the new value.
    "ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'customer'",
]


def run_light_migrations() -> None:
    if engine.dialect.name != "postgresql":
        return
    # AUTOCOMMIT: ALTER TYPE ... ADD VALUE cannot run inside a transaction on older PostgreSQL.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for statement in COLUMN_STATEMENTS:
            try:
                conn.execute(text(statement))
            except Exception as exc:  # never block startup because of a migration hiccup
                print(f"[migrations] skipped: {statement[:60]}... ({exc})")
