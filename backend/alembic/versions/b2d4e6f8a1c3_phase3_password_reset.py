"""phase3_password_reset

Revision ID: b2d4e6f8a1c3
Revises: f3a7c9d2e8b1
Create Date: 2026-06-15

Phase 3 (T6 / F8) — password reset, full stack:
  - capsules: add content_unrecoverable (set true by the reset-with-data-loss
    path, FR-03, when a capsule's content was encrypted under a CEK that is
    no longer recoverable after the reset)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2d4e6f8a1c3"
down_revision: Union[str, None] = "f3a7c9d2e8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "capsules",
        sa.Column("content_unrecoverable", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("capsules", "content_unrecoverable")
