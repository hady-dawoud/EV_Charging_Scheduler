"""add reservation estimate snapshot

Revision ID: 0005_reservation_snapshot
Revises: 0004_create_charging_sessions
Create Date: 2026-05-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_reservation_snapshot"
down_revision: str | None = "0004_create_charging_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column("estimated_cost_gbp", sa.Float(), nullable=True),
    )
    op.add_column(
        "reservations",
        sa.Column("estimated_duration_minutes", sa.Float(), nullable=True),
    )
    op.add_column(
        "reservations",
        sa.Column("charger_label", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "reservations",
        sa.Column("distance_km", sa.Float(), nullable=True),
    )
    op.add_column(
        "reservations",
        sa.Column("score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reservations", "score")
    op.drop_column("reservations", "distance_km")
    op.drop_column("reservations", "charger_label")
    op.drop_column("reservations", "estimated_duration_minutes")
    op.drop_column("reservations", "estimated_cost_gbp")
