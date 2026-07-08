"""phase_b_demo_intervals

Revision ID: d7f1a3c9e5b2
Revises: c1e5d8f2a4b7
Create Date: 2026-07-04

Phase B schema changes:
  - checkin_schedules: add check_interval_minutes, grace_period_minutes
    (nullable demo-mode overrides; NULL = use existing day-based columns,
    no backfill, no behavior change for existing rows).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d7f1a3c9e5b2"
down_revision: Union[str, None] = "c1e5d8f2a4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkin_schedules",
        sa.Column("check_interval_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "checkin_schedules",
        sa.Column("grace_period_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("checkin_schedules", "grace_period_minutes")
    op.drop_column("checkin_schedules", "check_interval_minutes")
