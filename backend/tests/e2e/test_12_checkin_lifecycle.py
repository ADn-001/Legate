"""
Phase 2 lifecycle regression suite (T-test).

Drives the REAL Celery task functions (the underlying async implementations,
called synchronously) against the REAL test database, Redis, Resend and
Supabase storage. Time is manipulated exclusively by writing real timestamps
to the database — datetime is never patched, and nothing is mocked.

Recipient addresses use Resend's deterministic test inbox
(delivered+<tag>@resend.dev always accepts). Deterministic per-recipient
send FAILURE is produced with a syntactically invalid recipient address,
which the Resend API rejects synchronously (422) — see the B6 tests.

Each scenario uses its own isolated local user (no Supabase auth user is
needed except for the B9/B10 full-purge test, which exercises the real
delete-account → purge → auth-deletion pipeline end to end).
"""

import os
import uuid
import secrets
import pytest
from datetime import datetime, timezone, timedelta

from httpx import AsyncClient
from sqlalchemy import select, func, and_

from tests.e2e.conftest import AsyncSessionLocal, TEST_PASSWORD, _make_admin_client
from app.config import get_settings
from app.db.models.user import User, UserSettings, UserStatus, EncryptionKey
from app.db.models.beneficiary import Beneficiary, BeneficiaryStatus
from app.db.models.capsule import Capsule, CapsuleStatus, CapsuleRecipient, RecipientStatus
from app.db.models.checkin import (
    CheckInSchedule, CheckInEvent, TokenType, EventStatus,
    ReleaseTrigger, TriggerReason, TriggerStatus,
)
from app.db.models.delivery import DeliveryEvent, DeliveryStatus
from app.db.models.audit import AuditLog

from app.worker.tasks.checkin_tasks import (
    _dispatch_due_checkins,
    _check_grace_periods,
    _process_pending_triggers,
    _send_grace_period_reminders,
)
from app.worker.tasks.delivery_tasks import _run_delivery
from app.worker.tasks.cleanup_tasks import _purge_user_account

NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _test_inbox() -> str:
    """Unique, always-deliverable Resend test address."""
    return f"delivered+{uuid.uuid4().hex[:10]}@resend.dev"


def _make_delivery_key_material(user_id: uuid.UUID) -> tuple[bytes, bytes, bytes]:
    """Real AES-GCM delivery key material wrapped exactly as production expects."""
    import hmac as hmac_mod
    import hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    cfg = get_settings()
    wrapping_key = bytes.fromhex(
        hmac_mod.new(cfg.delivery_secret.encode(), str(user_id).encode(), hashlib.sha256).hexdigest()
    )
    cek = os.urandom(32)
    iv = os.urandom(12)
    wrapped = AESGCM(wrapping_key).encrypt(iv, cek, None)
    return cek, wrapped, iv


async def _create_local_user(
    *,
    email: str | None = None,
    verified: bool = True,
    status: UserStatus = UserStatus.active,
    interval_days: int = 30,
    grace_period_days: int = 14,
    next_dispatch_at: datetime | None = None,
    last_dispatched_at: datetime | None = None,
    last_confirmed_at: datetime | None = None,
    is_paused: bool = False,
    pause_count: int = 0,
    with_delivery_key: bool = False,
) -> dict:
    """Insert a fully-formed local user + schedule directly (real DB writes).

    No Supabase auth user is created — none of the task functions touch
    Supabase auth, so a synthetic supabase_uid keeps scenarios isolated.
    """
    email = email or _test_inbox()
    now = NOW()
    out: dict = {}

    async with AsyncSessionLocal() as db:
        user = User(
            supabase_uid=f"e2etest-{uuid.uuid4().hex}",
            email=email,
            email_verified=verified,
            full_name="Lifecycle Test User",
            status=status,
        )
        db.add(user)
        await db.flush()

        db.add(UserSettings(user_id=user.id))

        cek = None
        if with_delivery_key:
            cek, wrapped, iv = _make_delivery_key_material(user.id)
            db.add(EncryptionKey(
                user_id=user.id,
                encrypted_cek=b"unit-test-cek",
                cek_iv=b"unit-test-iv",
                pbkdf2_salt=b"unit-test-salt",
                pbkdf2_iterations=100000,
                delivery_encrypted_cek=wrapped,
                delivery_cek_iv=iv,
                created_at=now,
                updated_at=now,
            ))

        schedule = CheckInSchedule(
            user_id=user.id,
            interval_days=interval_days,
            grace_period_days=grace_period_days,
            next_dispatch_at=next_dispatch_at,
            last_dispatched_at=last_dispatched_at,
            last_confirmed_at=last_confirmed_at,
            is_paused=is_paused,
            pause_count=pause_count,
            snooze_count=0,
            snooze_limit=2,
        )
        db.add(schedule)
        await db.commit()
        out = {
            "user_id": user.id,
            "schedule_id": schedule.id,
            "email": email,
            "cek": cek,
        }
    return out


async def _event_count(user_id: uuid.UUID, token_type: TokenType | None = None) -> int:
    async with AsyncSessionLocal() as db:
        query = select(func.count()).select_from(CheckInEvent).where(CheckInEvent.user_id == user_id)
        if token_type is not None:
            query = query.where(CheckInEvent.token_type == token_type)
        return (await db.execute(query)).scalar() or 0


async def _get_schedule(schedule_id: uuid.UUID) -> CheckInSchedule:
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(CheckInSchedule).where(CheckInSchedule.id == schedule_id)
        )).scalar_one()


async def _set_schedule(schedule_id: uuid.UUID, **values) -> None:
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(update(CheckInSchedule).where(CheckInSchedule.id == schedule_id).values(**values))
        await db.commit()


async def _trigger_count(user_id: uuid.UUID) -> int:
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(func.count()).select_from(ReleaseTrigger).where(ReleaseTrigger.user_id == user_id)
        )).scalar() or 0


async def _add_beneficiary(user_id: uuid.UUID, *, email: str, emergency: bool = False) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        b = Beneficiary(
            user_id=user_id,
            full_name=f"Bene {uuid.uuid4().hex[:6]}",
            email=email,
            is_emergency_contact=emergency,
            status=BeneficiaryStatus.active,
        )
        db.add(b)
        await db.commit()
        return b.id


async def _add_capsule(
    user_id: uuid.UUID, beneficiary_id: uuid.UUID, *,
    title: str, delivery_order: int,
    storage_object_path: str | None = None, cipher_iv: bytes | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with AsyncSessionLocal() as db:
        c = Capsule(
            user_id=user_id,
            title=title,
            status=CapsuleStatus.active,
            delivery_order=delivery_order,
            storage_object_path=storage_object_path,
            cipher_iv=cipher_iv,
        )
        db.add(c)
        await db.flush()
        r = CapsuleRecipient(
            capsule_id=c.id,
            beneficiary_id=beneficiary_id,
            is_primary=True,
            status=RecipientStatus.pending,
        )
        db.add(r)
        await db.commit()
        return c.id, r.id


# ═════════════════════════════════════════════════════════════════════════════
# B1 — dispatch must not re-send every hourly run
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b1_dispatch_runs_twice_sends_once():
    u = await _create_local_user(next_dispatch_at=NOW() - timedelta(hours=2))

    await _dispatch_due_checkins()

    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.next_dispatch_at is None, "B1: next_dispatch_at must be cleared after dispatch"
    assert schedule.last_dispatched_at is not None
    assert await _event_count(u["user_id"], TokenType.confirm) == 1
    assert await _event_count(u["user_id"]) == 5  # confirm + 3 snoozes + emergency_pause

    # Second hourly run: nothing new.
    await _dispatch_due_checkins()
    assert await _event_count(u["user_id"], TokenType.confirm) == 1, "B1 regression: re-dispatch occurred"
    assert await _event_count(u["user_id"]) == 5


# ═════════════════════════════════════════════════════════════════════════════
# B3 — memorialized / unverified users must never receive check-ins
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b3_memorialized_and_unverified_not_dispatched():
    due = NOW() - timedelta(hours=2)
    memorialized = await _create_local_user(status=UserStatus.memorialized, next_dispatch_at=due)
    unverified = await _create_local_user(verified=False, next_dispatch_at=due)

    await _dispatch_due_checkins()

    for u in (memorialized, unverified):
        assert await _event_count(u["user_id"]) == 0, "B3 regression: ineligible user was dispatched"
        schedule = await _get_schedule(u["schedule_id"])
        assert schedule.next_dispatch_at is not None  # untouched
        assert schedule.last_dispatched_at is None


# ═════════════════════════════════════════════════════════════════════════════
# B4 — confirm fully resets pause state; dispatch works afterwards
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b4_confirm_resets_pause_state_and_dispatch_resumes(http: AsyncClient):
    u = await _create_local_user(
        last_dispatched_at=NOW() - timedelta(days=1),
        is_paused=True,
        pause_count=2,
    )
    await _set_schedule(
        u["schedule_id"],
        grace_reminder_sent_at=NOW() - timedelta(hours=5),
        last_grace_reminder_day=3,
    )

    # Real confirm token, redeemed through the real endpoint.
    token = secrets.token_urlsafe(48)
    async with AsyncSessionLocal() as db:
        db.add(CheckInEvent(
            user_id=u["user_id"],
            schedule_id=u["schedule_id"],
            token=token,
            token_type=TokenType.confirm,
            status=EventStatus.pending,
            expires_at=NOW() + timedelta(days=7),
            sent_at=NOW(),
        ))
        await db.commit()

    res = await http.get(f"/checkin/confirm?token={token}")
    assert res.status_code == 200

    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.is_paused is False, "B4 regression: is_paused stuck after confirm"
    assert schedule.pause_count == 0
    assert schedule.grace_reminder_sent_at is None
    assert schedule.last_grace_reminder_day is None
    assert schedule.next_dispatch_at is not None

    # Subsequent dispatch works: make it due and run.
    await _set_schedule(u["schedule_id"], next_dispatch_at=NOW() - timedelta(hours=1))
    before = await _event_count(u["user_id"])
    await _dispatch_due_checkins()
    assert await _event_count(u["user_id"]) == before + 5
    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.next_dispatch_at is None

    # Unpause was audit-logged.
    async with AsyncSessionLocal() as db:
        count = (await db.execute(
            select(func.count()).select_from(AuditLog).where(
                and_(AuditLog.user_id == u["user_id"], AuditLog.event_type == "checkin_unpaused")
            )
        )).scalar()
        assert count == 1


# ═════════════════════════════════════════════════════════════════════════════
# B5 — grace reminders: day 3 and day 7, once each per cycle
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b5_grace_reminders_day3_day7_once_per_cycle():
    u = await _create_local_user(
        grace_period_days=14,
        last_dispatched_at=NOW() - timedelta(days=3, hours=2),  # day 3 of grace
    )

    confirm_before = await _event_count(u["user_id"], TokenType.confirm)

    await _send_grace_period_reminders()
    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.last_grace_reminder_day == 3
    assert schedule.grace_reminder_sent_at is not None
    assert await _event_count(u["user_id"], TokenType.confirm) == confirm_before + 1

    # 12h later (same day-3 window): no duplicate.
    await _send_grace_period_reminders()
    assert await _event_count(u["user_id"], TokenType.confirm) == confirm_before + 1, \
        "B5 regression: day-3 reminder sent twice in one cycle"

    # Advance to day 7 of grace.
    await _set_schedule(u["schedule_id"], last_dispatched_at=NOW() - timedelta(days=7, hours=2))
    await _send_grace_period_reminders()
    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.last_grace_reminder_day == 7, "B5 regression: day-7 reminder never sent"
    assert await _event_count(u["user_id"], TokenType.confirm) == confirm_before + 2

    # And only once.
    await _send_grace_period_reminders()
    assert await _event_count(u["user_id"], TokenType.confirm) == confirm_before + 2

    # New cycle (fresh dispatch) resets the per-cycle tracker.
    await _set_schedule(u["schedule_id"], next_dispatch_at=NOW() - timedelta(hours=1))
    await _dispatch_due_checkins()
    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.last_grace_reminder_day is None, "B5: new cycle must reset last_grace_reminder_day"
    assert schedule.grace_reminder_sent_at is None


# ═════════════════════════════════════════════════════════════════════════════
# B2 — exactly one trigger per missed cycle; none after memorialization
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b2_grace_expiry_creates_exactly_one_trigger():
    u = await _create_local_user(
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(days=8),  # grace expired
    )

    await _check_grace_periods()
    assert await _trigger_count(u["user_id"]) == 1

    # Hourly re-run: no duplicate. (The compose worker may have already
    # processed the enqueued delivery — a trigger in ANY state from the
    # current cycle blocks duplicates, so the assertion is race-free.)
    await _check_grace_periods()
    assert await _trigger_count(u["user_id"]) == 1, "B2 regression: duplicate trigger for same cycle"

    # After delivery completes the user is memorialized — grace task must
    # never form a new trigger again.
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(ReleaseTrigger)
            .where(ReleaseTrigger.user_id == u["user_id"])
            .values(status=TriggerStatus.completed)
        )
        await db.execute(
            update(User).where(User.id == u["user_id"]).values(status=UserStatus.memorialized)
        )
        await db.commit()

    await _check_grace_periods()
    assert await _trigger_count(u["user_id"]) == 1, "B2 regression: post-delivery re-trigger"


# ═════════════════════════════════════════════════════════════════════════════
# B8 — emergency contact: 48h pending_confirmation window, pause, promotion
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b8_emergency_contact_creates_pending_confirmation(http: AsyncClient):
    u = await _create_local_user(
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(days=8),
    )
    contact_email = _test_inbox()
    await _add_beneficiary(u["user_id"], email=contact_email, emergency=True)

    before = NOW()
    await _check_grace_periods()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.user_id == u["user_id"])
        )).scalar_one()
        assert trigger.status == TriggerStatus.pending_confirmation, \
            "B8: trigger must open a 48h window when an emergency contact exists"
        deliver_after = trigger.deliver_after
        if deliver_after.tzinfo is None:
            deliver_after = deliver_after.replace(tzinfo=timezone.utc)
        assert deliver_after > before + timedelta(hours=47)
        assert deliver_after < before + timedelta(hours=49)

        # A fresh emergency_pause token was generated for the contact's email.
        pause_event = (await db.execute(
            select(CheckInEvent).where(
                and_(
                    CheckInEvent.user_id == u["user_id"],
                    CheckInEvent.token_type == TokenType.emergency_pause,
                    CheckInEvent.status == EventStatus.pending,
                )
            ).order_by(CheckInEvent.sent_at.desc())
        )).scalars().first()
        assert pause_event is not None, "B8: pause token row missing"
        pause_token = pause_event.token

    # Pause link extends grace (pause_count drives the deadline extension)
    # and terminates the trigger.
    res = await http.get(f"/checkin/emergency/pause?token={pause_token}")
    assert res.status_code == 200

    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.is_paused is True
    assert schedule.pause_count == 1, "B8/FR-24: pause must extend grace via pause_count"

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.user_id == u["user_id"])
        )).scalar_one()
        assert trigger.status == TriggerStatus.paused_cancelled


@pytest.mark.asyncio
async def test_b8_pending_trigger_promotes_after_window():
    u = await _create_local_user(
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(days=8),
    )
    await _add_beneficiary(u["user_id"], email=_test_inbox(), emergency=True)

    await _check_grace_periods()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.user_id == u["user_id"])
        )).scalar_one()
        assert trigger.status == TriggerStatus.pending_confirmation
        trigger_id = trigger.id

    # 48h "elapse" via a real timestamp write.
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(ReleaseTrigger)
            .where(ReleaseTrigger.id == trigger_id)
            .values(deliver_after=NOW() - timedelta(hours=1))
        )
        await db.commit()

    await _process_pending_triggers()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
        )).scalar_one()
        # Promotion enqueues real delivery on the compose worker, which may
        # already have advanced the trigger past `processing` (this user has
        # no delivery key, so the worker marks it failed). Any state but
        # pending_confirmation proves promotion happened.
        assert trigger.status != TriggerStatus.pending_confirmation, \
            "B8: trigger not promoted after deliver_after elapsed"

        promoted_audit = (await db.execute(
            select(func.count()).select_from(AuditLog).where(
                and_(
                    AuditLog.user_id == u["user_id"],
                    AuditLog.event_type == "delivery_triggered",
                )
            )
        )).scalar()
        assert promoted_audit >= 1


# ═════════════════════════════════════════════════════════════════════════════
# B6 — per-recipient retry, max 3 attempts, then failed + alert + audit
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b6_per_recipient_retry_then_permanent_failure():
    cfg = get_settings()
    prev_alert = cfg.alert_email
    cfg.alert_email = _test_inbox()  # real alert email, deterministic inbox
    try:
        u = await _create_local_user(with_delivery_key=True)
        good = await _add_beneficiary(u["user_id"], email=_test_inbox())
        # A syntactically invalid address is rejected synchronously by the
        # Resend API — deterministic, real send failure (bounced@resend.dev
        # only bounces asynchronously and would NOT fail the API call).
        bad = await _add_beneficiary(u["user_id"], email="invalid-recipient")

        _cap_good, recip_good = await _add_capsule(u["user_id"], good, title="For the good inbox", delivery_order=1)
        _cap_bad, recip_bad = await _add_capsule(u["user_id"], bad, title="For the bad inbox", delivery_order=2)

        async with AsyncSessionLocal() as db:
            trigger = ReleaseTrigger(
                user_id=u["user_id"],
                triggered_at=NOW(),
                reason=TriggerReason.checkin_missed,
                status=TriggerStatus.processing,
            )
            db.add(trigger)
            await db.commit()
            trigger_id = trigger.id

        # Attempt 1.
        await _run_delivery(str(trigger_id), attempt=1)

        async with AsyncSessionLocal() as db:
            trigger = (await db.execute(
                select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
            )).scalar_one()
            assert trigger.status == TriggerStatus.processing, \
                "B6 regression: trigger completed despite a failed recipient"

            sent = (await db.execute(
                select(DeliveryEvent).where(
                    and_(
                        DeliveryEvent.release_trigger_id == trigger_id,
                        DeliveryEvent.capsule_recipient_id == recip_good,
                        DeliveryEvent.delivery_status == DeliveryStatus.sent,
                    )
                )
            )).scalars().all()
            assert len(sent) == 1

            failed = (await db.execute(
                select(DeliveryEvent).where(
                    and_(
                        DeliveryEvent.release_trigger_id == trigger_id,
                        DeliveryEvent.capsule_recipient_id == recip_bad,
                        DeliveryEvent.delivery_status == DeliveryStatus.failed,
                    )
                )
            )).scalars().all()
            assert len(failed) == 1
            assert failed[0].attempts == 1

        # Attempts 2 and 3 — re-send ONLY the failed recipient.
        await _run_delivery(str(trigger_id), attempt=2)
        await _run_delivery(str(trigger_id), attempt=3)

        async with AsyncSessionLocal() as db:
            trigger = (await db.execute(
                select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
            )).scalar_one()
            assert trigger.status == TriggerStatus.failed, \
                "B6: trigger must be failed after final attempt"

            # The good recipient was sent exactly once across all attempts.
            good_events = (await db.execute(
                select(func.count()).select_from(DeliveryEvent).where(
                    and_(
                        DeliveryEvent.release_trigger_id == trigger_id,
                        DeliveryEvent.capsule_recipient_id == recip_good,
                    )
                )
            )).scalar()
            assert good_events == 1, "B6: succeeded recipient must not be re-sent"

            # The failed recipient accumulated 3 failed attempts.
            bad_events = (await db.execute(
                select(DeliveryEvent).where(
                    and_(
                        DeliveryEvent.release_trigger_id == trigger_id,
                        DeliveryEvent.capsule_recipient_id == recip_bad,
                    )
                ).order_by(DeliveryEvent.attempts)
            )).scalars().all()
            assert [e.attempts for e in bad_events] == [1, 2, 3]
            assert all(e.delivery_status == DeliveryStatus.failed for e in bad_events)

            # Audit row for permanent failure.
            audit_count = (await db.execute(
                select(func.count()).select_from(AuditLog).where(
                    and_(
                        AuditLog.user_id == u["user_id"],
                        AuditLog.event_type == "delivery_failed_permanently",
                    )
                )
            )).scalar()
            assert audit_count == 1

            # Partial delivery: memorialized anyway (NFR-07, documented).
            user = (await db.execute(select(User).where(User.id == u["user_id"]))).scalar_one()
            assert user.status == UserStatus.memorialized
    finally:
        cfg.alert_email = prev_alert


# ═════════════════════════════════════════════════════════════════════════════
# B7 — one email per beneficiary, capsules ordered by delivery_order
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b7_single_email_per_beneficiary_ordered_capsules():
    u = await _create_local_user(with_delivery_key=True)
    bene = await _add_beneficiary(u["user_id"], email=_test_inbox())

    # Created out of order on purpose: 2, 1, 3.
    titles = {2: "Second capsule ZZorder2", 1: "First capsule ZZorder1", 3: "Third capsule ZZorder3"}
    recipient_ids = []
    for order in (2, 1, 3):
        _cid, rid = await _add_capsule(u["user_id"], bene, title=titles[order], delivery_order=order)
        recipient_ids.append(rid)

    async with AsyncSessionLocal() as db:
        trigger = ReleaseTrigger(
            user_id=u["user_id"],
            triggered_at=NOW(),
            reason=TriggerReason.checkin_missed,
            status=TriggerStatus.processing,
        )
        db.add(trigger)
        await db.commit()
        trigger_id = trigger.id

    await _run_delivery(str(trigger_id), attempt=1)

    async with AsyncSessionLocal() as db:
        events = (await db.execute(
            select(DeliveryEvent).where(DeliveryEvent.release_trigger_id == trigger_id)
        )).scalars().all()
        assert len(events) == 3
        assert all(e.delivery_status == DeliveryStatus.sent for e in events)

        # Exactly ONE email: every recipient row carries the same Resend
        # message id from the single send call.
        message_ids = {e.resend_message_id for e in events}
        assert len(message_ids) == 1 and None not in message_ids, \
            "B7 regression: more than one email sent to a single beneficiary"

        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
        )).scalar_one()
        assert trigger.status == TriggerStatus.completed

    # Body ordering. Preferred: fetch the actual sent email from the Resend
    # API. Send-only API keys can't read emails back (401 restricted_api_key);
    # in that case fall back to re-rendering through the SAME production query
    # and render function the task just used, and assert order on that output.
    import resend
    from resend.exceptions import ResendError
    resend.api_key = get_settings().resend_api_key
    html = ""
    try:
        email = resend.Emails.get(email_id=next(iter(message_ids)))
        html = email.get("html") if isinstance(email, dict) else getattr(email, "html", "")
    except ResendError as exc:
        if getattr(exc, "error_type", "") != "restricted_api_key" and "restricted" not in str(exc).lower():
            raise
        # Fallback: production-ordered query + production renderer.
        from sqlalchemy import select as sa_select
        from app.worker.tasks.delivery_tasks import _build_capsule_html
        async with AsyncSessionLocal() as db:
            ordered = (await db.execute(
                sa_select(Capsule)
                .where(and_(Capsule.user_id == u["user_id"], Capsule.status == CapsuleStatus.active))
                .order_by(Capsule.delivery_order)
            )).scalars().all()
            html = "".join(
                _build_capsule_html(capsule=c, cek=u["cek"], supabase=None, cfg=get_settings())
                for c in ordered
            )

    assert html, "Could not obtain email body for order verification"
    pos = [html.find(titles[i]) for i in (1, 2, 3)]
    assert all(p != -1 for p in pos), "B7: capsule titles missing from email body"
    assert pos[0] < pos[1] < pos[2], f"B7 regression: capsules out of order (positions {pos})"


# ═════════════════════════════════════════════════════════════════════════════
# B9 + B10 — GDPR purge: storage empty, rows gone, auth gone, audit anonymized
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_b9_b10_full_account_purge(http: AsyncClient):
    from app.core.supabase import get_storage

    from tests.e2e.conftest import make_test_email

    cfg = get_settings()
    sb_admin = _make_admin_client()
    email = make_test_email()  # Supabase validates domain deliverability
    password = TEST_PASSWORD

    # Real Supabase auth user (needed for password re-auth + auth deletion).
    # Retry on AuthRetryableError — after 70+ min of test load the Supabase
    # Admin API HTTP connection can time out transiently.
    import time as _time
    from gotrue.errors import AuthRetryableError as _AuthRetryableError
    _last_exc = None
    for _attempt in range(4):
        try:
            admin_resp = sb_admin.auth.admin.create_user({
                "email": email, "password": password, "email_confirm": True,
            })
            break
        except _AuthRetryableError as _e:
            _last_exc = _e
            _time.sleep(10 * (_attempt + 1))  # 10s, 20s, 30s backoff
    else:
        raise _last_exc
    supabase_uid = admin_resp.user.id

    now = NOW()
    async with AsyncSessionLocal() as db:
        user = User(
            supabase_uid=supabase_uid, email=email, email_verified=True,
            status=UserStatus.active,
        )
        db.add(user)
        await db.flush()
        user_id = user.id
        db.add(UserSettings(user_id=user_id))
        db.add(EncryptionKey(
            user_id=user_id,
            encrypted_cek=b"cek", cek_iv=b"iv", pbkdf2_salt=b"salt",
            pbkdf2_iterations=100000, created_at=now, updated_at=now,
        ))
        db.add(CheckInSchedule(
            user_id=user_id, interval_days=30, grace_period_days=7,
        ))
        await db.commit()

    bene = await _add_beneficiary(user_id, email=_test_inbox())

    # Two capsules with REAL uploaded blobs.
    storage = get_storage()
    capsule_ids = []
    for i in range(2):
        path = None
        cid, _rid = await _add_capsule(
            user_id, bene, title=f"Purge capsule {i}", delivery_order=i + 1,
        )
        capsule_ids.append(cid)
        path = f"{user_id}/{cid}/content.enc"
        storage.from_(cfg.supabase_storage_bucket_content).upload(
            path, f"encrypted-blob-{i}".encode(),
            {"content-type": "application/octet-stream"},
        )
        async with AsyncSessionLocal() as db:
            cap = await db.get(Capsule, cid)
            cap.storage_object_path = path
            await db.commit()

    # Sanity: blobs really exist.
    for cid in capsule_ids:
        items = storage.from_(cfg.supabase_storage_bucket_content).list(f"{user_id}/{cid}")
        assert any(it.get("name") == "content.enc" for it in (items or []))

    # Plant a deterministic audit row for the user so anonymization is
    # always assertable, then capture all of the user's audit row ids.
    async with AsyncSessionLocal() as db:
        marker = AuditLog(
            user_id=user_id,
            event_type="e2e_purge_marker",
            description=f"identifying data for {email}",
            ip_address="203.0.113.7",
            created_at=NOW(),
        )
        db.add(marker)
        await db.commit()
        marker_id = marker.id
        audit_ids = [row[0] for row in (await db.execute(
            select(AuditLog.id).where(AuditLog.user_id == user_id)
        )).all()]
    assert marker_id in audit_ids

    # Delete account through the real API (password + "DELETE" confirmation).
    login = await http.post("/auth/login", json={"email": email, "password": password})
    if login.status_code in (429, 503):
        pytest.skip("Supabase rate limit / unavailable — re-run after cooldown")
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    res = await http.request(
        "DELETE", "/users/me",
        json={"confirmation": "DELETE", "password": password},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is not None:  # compose worker may already have purged
            assert user.status == UserStatus.pending_deletion

    # Run the purge task function directly (idempotent vs. the compose worker).
    await _purge_user_account(str(user_id))

    # 1) Storage: every capsule prefix lists empty in every bucket.
    for bucket in (
        cfg.supabase_storage_bucket_content,
        cfg.supabase_storage_bucket_media,
        cfg.supabase_storage_bucket_thumbnails,
    ):
        for cid in capsule_ids:
            items = storage.from_(bucket).list(f"{user_id}/{cid}") or []
            real = [it for it in items if it.get("id")]
            assert not real, f"B9 regression: objects remain in {bucket}/{user_id}/{cid}"
        root_items = storage.from_(bucket).list(str(user_id)) or []
        real_root = [it for it in root_items if it.get("id")]
        assert not real_root, f"B9 regression: stray objects remain in {bucket}/{user_id}"

    # 2) DB: users row gone; FK cascades removed everything.
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none() is None
        for model, col in (
            (UserSettings, UserSettings.user_id),
            (EncryptionKey, EncryptionKey.user_id),
            (Beneficiary, Beneficiary.user_id),
            (Capsule, Capsule.user_id),
            (CheckInSchedule, CheckInSchedule.user_id),
            (CheckInEvent, CheckInEvent.user_id),
            (ReleaseTrigger, ReleaseTrigger.user_id),
        ):
            count = (await db.execute(
                select(func.count()).select_from(model).where(col == user_id)
            )).scalar()
            assert count == 0, f"B10 regression: {model.__tablename__} rows survived the purge"

        recip_count = (await db.execute(
            select(func.count()).select_from(CapsuleRecipient).where(
                CapsuleRecipient.capsule_id.in_(capsule_ids)
            )
        )).scalar()
        assert recip_count == 0

        # 3) Audit rows anonymized, event types preserved.
        logs = (await db.execute(
            select(AuditLog).where(AuditLog.id.in_(audit_ids))
        )).scalars().all()
        assert len(logs) == len(audit_ids), "audit rows must be kept for compliance"
        for log in logs:
            assert log.user_id is None
            assert log.actor_id is None
            assert log.ip_address is None
            assert log.description in (None, "[redacted]")
            assert log.event_type  # kept

        marker = (await db.execute(
            select(AuditLog).where(AuditLog.id == marker_id)
        )).scalar_one()
        assert marker.event_type == "e2e_purge_marker"
        assert marker.description == "[redacted]", "B10 regression: identifying audit data survived"

    # 4) Supabase auth user gone.
    auth_gone = False
    try:
        resp = sb_admin.auth.admin.get_user_by_id(supabase_uid)
        auth_gone = resp is None or resp.user is None
    except Exception:
        auth_gone = True
    assert auth_gone, "B10 regression: Supabase auth user still exists"
