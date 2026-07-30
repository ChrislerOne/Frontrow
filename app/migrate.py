"""Additive column migrations for SQLite.

`Base.metadata.create_all()` creates missing *tables* but never adds a column to a
table that already exists, so a new field on an existing model is invisible to the
live database until an explicit ALTER TABLE runs. Every entry here is idempotent —
applied only when the column is absent — and additive, so no data is ever dropped.
"""

from sqlalchemy import Engine

NEW_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "default_city": "VARCHAR",
    },
    "lists": {
        "share_note": "VARCHAR",
    },
    "artists": {
        "last_checked_at": "DATETIME",
        "image": "VARCHAR",
    },
    "events": {
        "status": "VARCHAR",
        "in_stock": "BOOLEAN",
        "price": "FLOAT",
        "currency": "VARCHAR",
        "last_checked_at": "DATETIME",
    },
}


def ensure_columns(engine: Engine) -> list[str]:
    applied = []
    with engine.begin() as conn:
        for table, columns in NEW_COLUMNS.items():
            present = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if not present:
                continue  # table doesn't exist yet — create_all builds it with the column
            for column, ddl_type in columns.items():
                if column not in present:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                    applied.append(f"{table}.{column}")
    return applied
