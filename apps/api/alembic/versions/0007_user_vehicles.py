"""create user vehicle profiles

Revision ID: 0007_user_vehicles
Revises: 0006_password_reset_tokens
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_user_vehicles"
down_revision: str | None = "0006_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("make", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("battery_capacity_kwh", sa.Float(), nullable=False),
        sa.Column("current_soc", sa.Float(), nullable=False),
        sa.Column("range_km", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_vehicles_user_id", "user_vehicles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_vehicles_user_id", table_name="user_vehicles")
    op.drop_table("user_vehicles")
