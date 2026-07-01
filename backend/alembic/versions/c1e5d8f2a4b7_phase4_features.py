"""phase4_features

Revision ID: c1e5d8f2a4b7
Revises: b2d4e6f8a1c3
Create Date: 2026-06-24

Phase 4 schema changes:
  - user_settings: add setup_step (T5 — wizard resumability)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1e5d8f2a4b7"
down_revision: Union[str, None] = "b2d4e6f8a1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("setup_step", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "setup_step")
