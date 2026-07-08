"""phase_b_emergency_confirm_minutes

Revision ID: e9b3f6a1c8d4
Revises: d7f1a3c9e5b2
Create Date: 2026-07-06

Phase B (extension) schema changes:
  - checkin_schedules: add emergency_confirm_minutes (nullable demo-mode
    override for the FR-23 48h emergency-contact confirmation window; NULL =
    use the existing hardcoded 48h default, no backfill, no behavior change
    for existing rows).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e9b3f6a1c8d4"
down_revision: Union[str, None] = "d7f1a3c9e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkin_schedules",
        sa.Column("emergency_confirm_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("checkin_schedules", "emergency_confirm_minutes")
