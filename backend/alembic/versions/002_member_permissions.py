"""Household member fine-grained permissions."""

from alembic import op
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint, inspect

revision = "002_member_permissions"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "member_permissions" in inspect(bind).get_table_names():
        return
    op.create_table(
        "member_permissions",
        Column("id", String(36), primary_key=True),
        Column(
            "member_id",
            String(36),
            ForeignKey("household_members.id"),
            index=True,
            nullable=False,
        ),
        Column("resource", String(128), nullable=False),
        Column("action", String(32), nullable=False),
        UniqueConstraint("member_id", "resource", "action", name="uq_member_perm"),
    )


def downgrade() -> None:
    op.drop_table("member_permissions")
