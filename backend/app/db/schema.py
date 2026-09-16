from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.base import Base

_EXTRA_COLUMNS: dict[str, dict[str, str]] = {
    "medications": {
        "flags": "JSON",
        "quantity_on_hand": "FLOAT",
        "refill_quantity": "FLOAT",
        "refill_reminder_level": "FLOAT",
        "refills_remaining": "INTEGER",
        "pharmacy": "VARCHAR(255)",
        "rx_number": "VARCHAR(64)",
        "last_refill_on": "DATE",
    },
    "household_otc_medications": {
        "quantity_on_hand": "FLOAT",
        "refill_quantity": "FLOAT",
        "refill_reminder_level": "FLOAT",
        "last_refill_on": "DATE",
    },
}


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    for table, columns in _EXTRA_COLUMNS.items():
        if table not in inspector.get_table_names():
            continue
        existing = {item["name"] for item in inspector.get_columns(table)}
        missing = [(name, ddl) for name, ddl in columns.items() if name not in existing]
        if not missing:
            continue
        with engine.begin() as connection:
            for name, ddl in missing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
