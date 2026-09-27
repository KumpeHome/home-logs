"""Notification preferences, subscriptions, and delivery log."""

from __future__ import annotations

from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    inspect,
)

revision = "004_notifications"
down_revision = "003_medication_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "notification_preferences" not in tables:
        op.create_table(
            "notification_preferences",
            Column("id", String(36), primary_key=True),
            Column(
                "member_id",
                String(36),
                ForeignKey("household_members.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            Column("email_enabled", Boolean, nullable=False),
            Column("pushover_enabled", Boolean, nullable=False),
            Column("pushover_user_key", String(128), nullable=True),
            Column("pushover_key_source", String(32), nullable=True),
            Column("pushover_link_hash", String(64), nullable=True),
            Column("pushover_link_expires_at", DateTime, nullable=True),
            Column("dose_lead_minutes", Integer, nullable=False),
        )
    if "notification_subscriptions" not in tables:
        op.create_table(
            "notification_subscriptions",
            Column("id", String(36), primary_key=True),
            Column(
                "member_id",
                String(36),
                ForeignKey("household_members.id", ondelete="CASCADE"),
                nullable=False,
            ),
            Column("topic", String(64), nullable=False),
            Column("subject_member_id", String(36), nullable=False),
            UniqueConstraint(
                "member_id", "topic", "subject_member_id", name="uq_notification_sub"
            ),
        )
    if "notification_deliveries" not in tables:
        op.create_table(
            "notification_deliveries",
            Column("id", String(36), primary_key=True),
            Column(
                "recipient_member_id",
                String(36),
                ForeignKey("household_members.id", ondelete="CASCADE"),
                nullable=False,
            ),
            Column("channel", String(32), nullable=False),
            Column("dedupe_key", String(255), nullable=False),
            Column("topic", String(64), nullable=False),
            Column("created_at", DateTime, nullable=True),
            UniqueConstraint(
                "recipient_member_id",
                "channel",
                "dedupe_key",
                name="uq_notification_delivery",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "notification_deliveries" in tables:
        op.drop_table("notification_deliveries")
    if "notification_subscriptions" in tables:
        op.drop_table("notification_subscriptions")
    if "notification_preferences" in tables:
        op.drop_table("notification_preferences")
