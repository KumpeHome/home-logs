"""Dose administration window and repeat settings on notification preferences."""

from __future__ import annotations

from sqlalchemy import Column, Integer, inspect

from alembic import op

revision = "005_notification_dose_rules"
down_revision = "004_notifications"
branch_labels = None
depends_on = None

_COLUMNS = (
    Column("dose_window_before_minutes", Integer, nullable=False, server_default="30"),
    Column("dose_window_after_minutes", Integer, nullable=False, server_default="60"),
    Column("dose_repeat_count", Integer, nullable=False, server_default="1"),
    Column(
        "dose_repeat_interval_minutes", Integer, nullable=False, server_default="15"
    ),
)


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "notification_preferences" not in inspector.get_table_names():
        return
    existing = {
        item["name"] for item in inspector.get_columns("notification_preferences")
    }
    for column in _COLUMNS:
        if column.name not in existing:
            op.add_column("notification_preferences", column)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "notification_preferences" not in inspector.get_table_names():
        return
    existing = {
        item["name"] for item in inspector.get_columns("notification_preferences")
    }
    for column in reversed(_COLUMNS):
        if column.name in existing:
            op.drop_column("notification_preferences", column.name)
