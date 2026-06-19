"""phase2_logic_fixes

Revision ID: a4c91f02d7e1
Revises: 6859bb69b2d3
Create Date: 2026-06-12

Phase 2 (backend logic bugs) schema changes:
  - checkin_schedules: add last_grace_reminder_day (T5 / B5)
  - release_triggers: add deliver_after; new triggerstatus values
    pending_confirmation + paused_cancelled (T6 / B8)
  - userstatus: new value pending_deletion (T7 / B10)
  - capsules: add content_size_bytes (T13 / B16)
  - FK ondelete fixes so a hard DELETE of users cascades cleanly (T7 / B10):
      release_triggers.user_id           RESTRICT  -> CASCADE
      capsule_recipients.beneficiary_id  RESTRICT  -> CASCADE
      delivery_events.release_trigger_id NO ACTION -> CASCADE
      delivery_events.capsule_recipient_id NO ACTION -> CASCADE
      checkin_events.schedule_id         NO ACTION -> CASCADE
      audit_logs.user_id                 NO ACTION -> SET NULL
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a4c91f02d7e1"
down_revision: Union[str, None] = "6859bb69b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New enum values (must run outside the migration transaction) ────────
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE triggerstatus ADD VALUE IF NOT EXISTS 'pending_confirmation' BEFORE 'processing'")
        op.execute("ALTER TYPE triggerstatus ADD VALUE IF NOT EXISTS 'paused_cancelled'")
        op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'pending_deletion' BEFORE 'deleted'")

    # ── New columns ─────────────────────────────────────────────────────────
    op.add_column("checkin_schedules", sa.Column("last_grace_reminder_day", sa.Integer(), nullable=True))
    op.add_column("release_triggers", sa.Column("deliver_after", sa.DateTime(timezone=True), nullable=True))
    op.add_column("capsules", sa.Column("content_size_bytes", sa.BigInteger(), nullable=True))

    # ── FK ondelete fixes ────────────────────────────────────────────────────
    op.drop_constraint("release_triggers_user_id_fkey", "release_triggers", type_="foreignkey")
    op.create_foreign_key(
        "release_triggers_user_id_fkey", "release_triggers", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("capsule_recipients_beneficiary_id_fkey", "capsule_recipients", type_="foreignkey")
    op.create_foreign_key(
        "capsule_recipients_beneficiary_id_fkey", "capsule_recipients", "beneficiaries",
        ["beneficiary_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("delivery_events_release_trigger_id_fkey", "delivery_events", type_="foreignkey")
    op.create_foreign_key(
        "delivery_events_release_trigger_id_fkey", "delivery_events", "release_triggers",
        ["release_trigger_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("delivery_events_capsule_recipient_id_fkey", "delivery_events", type_="foreignkey")
    op.create_foreign_key(
        "delivery_events_capsule_recipient_id_fkey", "delivery_events", "capsule_recipients",
        ["capsule_recipient_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("checkin_events_schedule_id_fkey", "checkin_events", type_="foreignkey")
    op.create_foreign_key(
        "checkin_events_schedule_id_fkey", "checkin_events", "checkin_schedules",
        ["schedule_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key(
        "audit_logs_user_id_fkey", "audit_logs", "users",
        ["user_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    # Enum values cannot be removed from PostgreSQL types; left in place.
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"])

    op.drop_constraint("checkin_events_schedule_id_fkey", "checkin_events", type_="foreignkey")
    op.create_foreign_key("checkin_events_schedule_id_fkey", "checkin_events", "checkin_schedules", ["schedule_id"], ["id"])

    op.drop_constraint("delivery_events_capsule_recipient_id_fkey", "delivery_events", type_="foreignkey")
    op.create_foreign_key("delivery_events_capsule_recipient_id_fkey", "delivery_events", "capsule_recipients", ["capsule_recipient_id"], ["id"])

    op.drop_constraint("delivery_events_release_trigger_id_fkey", "delivery_events", type_="foreignkey")
    op.create_foreign_key("delivery_events_release_trigger_id_fkey", "delivery_events", "release_triggers", ["release_trigger_id"], ["id"])

    op.drop_constraint("capsule_recipients_beneficiary_id_fkey", "capsule_recipients", type_="foreignkey")
    op.create_foreign_key("capsule_recipients_beneficiary_id_fkey", "capsule_recipients", "beneficiaries", ["beneficiary_id"], ["id"], ondelete="RESTRICT")

    op.drop_constraint("release_triggers_user_id_fkey", "release_triggers", type_="foreignkey")
    op.create_foreign_key("release_triggers_user_id_fkey", "release_triggers", "users", ["user_id"], ["id"], ondelete="RESTRICT")

    op.drop_column("capsules", "content_size_bytes")
    op.drop_column("release_triggers", "deliver_after")
    op.drop_column("checkin_schedules", "last_grace_reminder_day")
