"""Medication and OTC inventory columns for pill counts and refill reminders."""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, Integer, String, inspect

from alembic import op

revision = "003_medication_inventory"
down_revision = "002_member_permissions"
branch_labels = None
depends_on = None

_MEDICATION_COLUMNS = (
    Column("quantity_on_hand", Float, nullable=True),
    Column("refill_quantity", Float, nullable=True),
    Column("refill_reminder_level", Float, nullable=True),
    Column("refills_remaining", Integer, nullable=True),
    Column("pharmacy", String(255), nullable=True),
    Column("rx_number", String(64), nullable=True),
    Column("last_refill_on", Date, nullable=True),
)
_OTC_COLUMNS = (
    Column("quantity_on_hand", Float, nullable=True),
    Column("refill_quantity", Float, nullable=True),
    Column("refill_reminder_level", Float, nullable=True),
    Column("last_refill_on", Date, nullable=True),
)


def _existing_columns(table: str) -> set[str] | None:
    inspector = inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return None
    return {item["name"] for item in inspector.get_columns(table)}


def _add_missing(table: str, columns: tuple[Column, ...]) -> None:
    existing = _existing_columns(table)
    if existing is None:
        return
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column)


def _drop_present(table: str, columns: tuple[Column, ...]) -> None:
    existing = _existing_columns(table)
    if existing is None:
        return
    for column in reversed(columns):
        if column.name in existing:
            op.drop_column(table, column.name)


def upgrade() -> None:
    _add_missing("medications", _MEDICATION_COLUMNS)
    _add_missing("household_otc_medications", _OTC_COLUMNS)


def downgrade() -> None:
    _drop_present("household_otc_medications", _OTC_COLUMNS)
    _drop_present("medications", _MEDICATION_COLUMNS)
