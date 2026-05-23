"""phase2_schema

Revision ID: 6859bb69b2d3
Revises:
Create Date: 2026-05-22

Phase 2 schema changes:
  - users: add supabase_uid (NOT NULL), make password_hash nullable
  - encryption_keys: add delivery_encrypted_cek, delivery_cek_iv
  - checkin_schedules: add grace_reminder_sent_at
  - Initial creation of all tables if running on a fresh DB
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6859bb69b2d3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Create enums
    # -----------------------------------------------------------------------
    userstatus = sa.Enum("active", "suspended", "memorialized", "deleted", name="userstatus")
    beneficiarystatus = sa.Enum("active", "pending", "removed", name="beneficiarystatus")
    capsulestatus = sa.Enum("draft", "active", "pending_deletion", "deleted", "delivered", name="capsulestatus")
    recipientstatus = sa.Enum("pending", "queued", "sent", "failed", name="recipientstatus")
    mediatype = sa.Enum("photo", "video", name="mediatype")
    mediastatus = sa.Enum("uploading", "ready", "failed", "deleted", name="mediastatus")
    tokentype = sa.Enum("confirm", "snooze_7", "snooze_14", "snooze_30", "emergency_pause", name="tokentype")
    eventstatus = sa.Enum("pending", "used", "expired", name="eventstatus")
    triggerreason = sa.Enum("checkin_missed", "emergency_pause_timeout", "manual", name="triggerreason")
    triggerstatus = sa.Enum("processing", "completed", "failed", "cancelled", name="triggerstatus")
    deliverystatus = sa.Enum("pending", "sent", "bounced", "failed", "opened", name="deliverystatus")

    for e in (userstatus, beneficiarystatus, capsulestatus, recipientstatus,
              mediatype, mediastatus, tokentype, eventstatus, triggerreason,
              triggerstatus, deliverystatus):
        e.create(op.get_bind(), checkfirst=True)

    # -----------------------------------------------------------------------
    # users
    # -----------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supabase_uid", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("status", postgresql.ENUM("active", "suspended", "memorialized", "deleted", name="userstatus", create_type=False), nullable=True),
        sa.Column("erasure_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("supabase_uid"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_supabase_uid", "users", ["supabase_uid"])

    # -----------------------------------------------------------------------
    # user_settings
    # -----------------------------------------------------------------------
    op.create_table(
        "user_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("check_in_interval_days", sa.Integer(), nullable=True),
        sa.Column("grace_period_days", sa.Integer(), nullable=True),
        sa.Column("snooze_count_remaining", sa.Integer(), nullable=True),
        sa.Column("preferred_language", sa.String(8), nullable=True),
        sa.Column("needs_onboarding", sa.Boolean(), nullable=True),
        sa.Column("last_check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # -----------------------------------------------------------------------
    # encryption_keys
    # -----------------------------------------------------------------------
    op.create_table(
        "encryption_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("encrypted_cek", sa.LargeBinary(), nullable=False),
        sa.Column("cek_iv", sa.LargeBinary(), nullable=False),
        sa.Column("pbkdf2_salt", sa.LargeBinary(), nullable=False),
        sa.Column("pbkdf2_iterations", sa.Integer(), nullable=True),
        sa.Column("delivery_encrypted_cek", sa.LargeBinary(), nullable=True),
        sa.Column("delivery_cek_iv", sa.LargeBinary(), nullable=True),
        sa.Column("recovery_phrase_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # -----------------------------------------------------------------------
    # beneficiaries
    # -----------------------------------------------------------------------
    op.create_table(
        "beneficiaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("relationship", sa.String(64), nullable=True),
        sa.Column("is_emergency_contact", sa.Boolean(), nullable=True),
        sa.Column("status", postgresql.ENUM("active", "pending", "removed", name="beneficiarystatus", create_type=False), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -----------------------------------------------------------------------
    # capsules
    # -----------------------------------------------------------------------
    op.create_table(
        "capsules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", postgresql.ENUM("draft", "active", "pending_deletion", "deleted", "delivered", name="capsulestatus", create_type=False), nullable=True),
        sa.Column("storage_object_path", sa.Text(), nullable=True),
        sa.Column("cipher_iv", sa.LargeBinary(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("scheduled_delivery_date", sa.Date(), nullable=True),
        sa.Column("delivery_order", sa.Integer(), nullable=True),
        sa.Column("auto_saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capsules_user_id", "capsules", ["user_id"])

    # -----------------------------------------------------------------------
    # capsule_recipients
    # -----------------------------------------------------------------------
    op.create_table(
        "capsule_recipients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("capsule_id", sa.UUID(), nullable=True),
        sa.Column("beneficiary_id", sa.UUID(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "queued", "sent", "failed", name="recipientstatus", create_type=False), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["capsule_id"], ["capsules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -----------------------------------------------------------------------
    # media_attachments
    # -----------------------------------------------------------------------
    op.create_table(
        "media_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("capsule_id", sa.UUID(), nullable=True),
        sa.Column("type", postgresql.ENUM("photo", "video", name="mediatype", create_type=False), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_object_path", sa.Text(), nullable=False),
        sa.Column("cipher_iv", sa.LargeBinary(), nullable=False),
        sa.Column("thumbnail_storage_path", sa.Text(), nullable=True),
        sa.Column("video_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", postgresql.ENUM("uploading", "ready", "failed", "deleted", name="mediastatus", create_type=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["capsule_id"], ["capsules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -----------------------------------------------------------------------
    # checkin_schedules
    # -----------------------------------------------------------------------
    op.create_table(
        "checkin_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("grace_period_days", sa.Integer(), nullable=False),
        sa.Column("next_dispatch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snooze_count", sa.Integer(), nullable=True),
        sa.Column("snooze_limit", sa.Integer(), nullable=True),
        sa.Column("is_paused", sa.Boolean(), nullable=True),
        sa.Column("pause_count", sa.Integer(), nullable=True),
        sa.Column("grace_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_checkin_schedules_next_dispatch_at", "checkin_schedules", ["next_dispatch_at"])

    # -----------------------------------------------------------------------
    # checkin_events
    # -----------------------------------------------------------------------
    op.create_table(
        "checkin_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("token_type", postgresql.ENUM("confirm", "snooze_7", "snooze_14", "snooze_30", "emergency_pause", name="tokentype", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "used", "expired", name="eventstatus", create_type=False), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_ip", sa.String(45), nullable=True),
        sa.Column("click_user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["schedule_id"], ["checkin_schedules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_checkin_events_token", "checkin_events", ["token"])

    # -----------------------------------------------------------------------
    # release_triggers
    # -----------------------------------------------------------------------
    op.create_table(
        "release_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", postgresql.ENUM("checkin_missed", "emergency_pause_timeout", "manual", name="triggerreason", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("processing", "completed", "failed", "cancelled", name="triggerstatus", create_type=False), nullable=True),
        sa.Column("pause_count", sa.Integer(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -----------------------------------------------------------------------
    # delivery_events
    # -----------------------------------------------------------------------
    op.create_table(
        "delivery_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("release_trigger_id", sa.UUID(), nullable=True),
        sa.Column("capsule_recipient_id", sa.UUID(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_status", postgresql.ENUM("pending", "sent", "bounced", "failed", "opened", name="deliverystatus", create_type=False), nullable=True),
        sa.Column("resend_message_id", sa.String(255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["capsule_recipient_id"], ["capsule_recipients.id"]),
        sa.ForeignKeyConstraint(["release_trigger_id"], ["release_triggers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_events_release_trigger_id", "delivery_events", ["release_trigger_id"])

    # -----------------------------------------------------------------------
    # audit_logs
    # -----------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("delivery_events")
    op.drop_table("release_triggers")
    op.drop_table("checkin_events")
    op.drop_table("checkin_schedules")
    op.drop_table("media_attachments")
    op.drop_table("capsule_recipients")
    op.drop_table("capsules")
    op.drop_table("beneficiaries")
    op.drop_table("encryption_keys")
    op.drop_table("user_settings")
    op.drop_table("users")
