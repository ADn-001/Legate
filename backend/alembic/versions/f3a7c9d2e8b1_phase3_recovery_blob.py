"""phase3_recovery_blob

Revision ID: f3a7c9d2e8b1
Revises: a4c91f02d7e1
Create Date: 2026-06-15

Phase 3 (T4 / F4) — make the recovery phrase real:
  - encryption_keys: add recovery_encrypted_cek, recovery_cek_iv, recovery_salt
    (recovery_phrase_hash already exists from 6859bb69b2d3)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f3a7c9d2e8b1"
down_revision: Union[str, None] = "a4c91f02d7e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("encryption_keys", sa.Column("recovery_encrypted_cek", sa.LargeBinary(), nullable=True))
    op.add_column("encryption_keys", sa.Column("recovery_cek_iv", sa.LargeBinary(), nullable=True))
    op.add_column("encryption_keys", sa.Column("recovery_salt", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("encryption_keys", "recovery_salt")
    op.drop_column("encryption_keys", "recovery_cek_iv")
    op.drop_column("encryption_keys", "recovery_encrypted_cek")
