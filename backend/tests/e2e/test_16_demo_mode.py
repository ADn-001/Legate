"""
Phase B: demo-mode minute-level check-in intervals (T-test).

Covers:
  B-unit — interval_delta/grace_delta precedence (minutes override vs. NULL)
  B-403  — PATCH /settings/checkin with minute fields, DEMO_MODE off -> 403
  B-200  — PATCH /settings/checkin with minute fields, DEMO_MODE on -> columns
           set, next_dispatch_at recomputed in minutes
  B-clear — clear_minute_overrides resets to day-based scheduling
  B-lifecycle — full demo cycle (1-minute grace) drives a real release
           trigger via the real _check_grace_periods() task, exactly like
           the day-based path in test_12_checkin_lifecycle.py

The demo_mode flag lives on the shared, process-wide Settings singleton
(get_settings() is @lru_cache'd, so every caller shares one instance).
Tests that flip it restore the original value in `finally`, and any test
that mutates the shared session user's schedule resets it back to
day-based afterward — same pattern test_12's test_b6 uses for cfg.alert_email.
"""

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.core.scheduling import interval_delta, grace_delta, emergency_confirm_delta, EMERGENCY_CONFIRMATION_WINDOW_HOURS
from app.db.models.checkin import ReleaseTrigger, TriggerStatus

from tests.e2e.test_12_checkin_lifecycle import (
    _create_local_user,
    _set_schedule,
    _get_schedule,
    _trigger_count,
    _check_grace_periods,
    _process_pending_triggers,
    _add_beneficiary,
    _test_inbox,
    AsyncSessionLocal,
)
from sqlalchemy import select

NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


# ═════════════════════════════════════════════════════════════════════════════
# B-unit — interval_delta / grace_delta precedence
# ═════════════════════════════════════════════════════════════════════════════

def test_interval_delta_uses_days_when_minutes_null():
    schedule = SimpleNamespace(interval_days=30, check_interval_minutes=None)
    assert interval_delta(schedule) == timedelta(days=30)


def test_interval_delta_prefers_minutes_when_set():
    schedule = SimpleNamespace(interval_days=30, check_interval_minutes=2)
    assert interval_delta(schedule) == timedelta(minutes=2)


def test_grace_delta_uses_days_when_minutes_null():
    schedule = SimpleNamespace(grace_period_days=7, grace_period_minutes=None)
    assert grace_delta(schedule) == timedelta(days=7)


def test_grace_delta_prefers_minutes_when_set():
    schedule = SimpleNamespace(grace_period_days=7, grace_period_minutes=3)
    assert grace_delta(schedule) == timedelta(minutes=3)


def test_grace_delta_zero_minutes_falls_back_to_days():
    """0 is falsy — a schedule with grace_period_minutes=0 (never a real demo
    value; UI/schema floor is 1) must not silently produce a zero-length grace
    window. Falls back to the day-based column, same as NULL."""
    schedule = SimpleNamespace(grace_period_days=7, grace_period_minutes=0)
    assert grace_delta(schedule) == timedelta(days=7)


def test_emergency_confirm_delta_uses_48h_default_when_minutes_null():
    schedule = SimpleNamespace(emergency_confirm_minutes=None)
    assert emergency_confirm_delta(schedule) == timedelta(hours=EMERGENCY_CONFIRMATION_WINDOW_HOURS)
    assert emergency_confirm_delta(schedule) == timedelta(hours=48)


def test_emergency_confirm_delta_prefers_minutes_when_set():
    schedule = SimpleNamespace(emergency_confirm_minutes=5)
    assert emergency_confirm_delta(schedule) == timedelta(minutes=5)


def test_emergency_confirm_delta_zero_minutes_falls_back_to_default():
    """Same falsy-zero guard as grace_delta — 0 is never a real demo value
    (schema floor is 1), so it must not produce a zero-length window."""
    schedule = SimpleNamespace(emergency_confirm_minutes=0)
    assert emergency_confirm_delta(schedule) == timedelta(hours=48)


# ═════════════════════════════════════════════════════════════════════════════
# B-403 / B-200 / B-clear — PATCH /settings/checkin demo-mode gating
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_patch_minutes_rejected_when_demo_mode_off(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = False
    try:
        res = await auth_client.patch("/settings/checkin", json={"check_interval_minutes": 5})
        assert res.status_code == 403, (
            f"B4: expected 403 with DEMO_MODE off, got {res.status_code}: {res.text}"
        )
        assert "demo mode" in res.text.lower()
    finally:
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_patch_clear_minute_overrides_rejected_when_demo_mode_off(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = False
    try:
        res = await auth_client.patch("/settings/checkin", json={"clear_minute_overrides": True})
        assert res.status_code == 403
    finally:
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_patch_minutes_accepted_when_demo_mode_on(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = True
    try:
        before = NOW()
        res = await auth_client.patch(
            "/settings/checkin",
            json={"check_interval_minutes": 5, "grace_period_minutes": 3},
        )
        assert res.status_code == 200, f"B4: {res.status_code}: {res.text}"
        body = res.json()
        assert body["check_interval_minutes"] == 5
        assert body["grace_period_minutes"] == 3
        assert body["demo_mode"] is True

        next_dispatch = datetime.fromisoformat(body["next_dispatch_at"].replace("Z", "+00:00"))
        # Anchored to now (no last_confirmed_at yet for a brand-new dispatch)
        # or to last_confirmed_at — either way it must land ~5 minutes out,
        # not ~30 days (the old day-based math would have produced that).
        assert next_dispatch - before < timedelta(minutes=6), (
            "B4: next_dispatch_at was not recomputed in minutes"
        )
    finally:
        # B4: reset the shared session user's schedule back to day-based so
        # other test modules relying on this fixture see normal-mode state.
        clear_res = await auth_client.patch("/settings/checkin", json={"clear_minute_overrides": True})
        assert clear_res.status_code == 200
        assert clear_res.json()["check_interval_minutes"] is None
        assert clear_res.json()["grace_period_minutes"] is None
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_patch_emergency_confirm_minutes_rejected_when_demo_mode_off(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = False
    try:
        res = await auth_client.patch("/settings/checkin", json={"emergency_confirm_minutes": 5})
        assert res.status_code == 403, (
            f"expected 403 with DEMO_MODE off, got {res.status_code}: {res.text}"
        )
        assert "demo mode" in res.text.lower()
    finally:
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_patch_emergency_confirm_minutes_accepted_when_demo_mode_on(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = True
    try:
        res = await auth_client.patch("/settings/checkin", json={"emergency_confirm_minutes": 4})
        assert res.status_code == 200, f"{res.status_code}: {res.text}"
        body = res.json()
        assert body["emergency_confirm_minutes"] == 4
        assert body["demo_mode"] is True

        # clear_minute_overrides must reset this column too, alongside the
        # existing two.
        clear_res = await auth_client.patch("/settings/checkin", json={"clear_minute_overrides": True})
        assert clear_res.status_code == 200
        assert clear_res.json()["emergency_confirm_minutes"] is None
    finally:
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_get_checkin_settings_reports_demo_mode_flag(auth_client: AsyncClient):
    cfg = get_settings()
    prev = cfg.demo_mode
    try:
        cfg.demo_mode = True
        res = await auth_client.get("/settings/checkin")
        assert res.status_code == 200
        assert res.json()["demo_mode"] is True

        cfg.demo_mode = False
        res = await auth_client.get("/settings/checkin")
        assert res.status_code == 200
        assert res.json()["demo_mode"] is False
    finally:
        cfg.demo_mode = prev


@pytest.mark.asyncio
async def test_normal_mode_interval_patch_unaffected_by_phase_b(auth_client: AsyncClient):
    """Regression guard: a plain day-based PATCH (no minute fields) behaves
    exactly as it did before Phase B — demo_mode off, no 403, no minute
    columns touched."""
    cfg = get_settings()
    prev = cfg.demo_mode
    cfg.demo_mode = False
    try:
        res = await auth_client.patch("/settings/checkin", json={"interval_days": 45, "grace_period_days": 10})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["interval_days"] == 45
        assert body["grace_period_days"] == 10
        assert body["check_interval_minutes"] is None
        assert body["grace_period_minutes"] is None
    finally:
        # Restore prior defaults used by other modules' shared-user assumptions.
        await auth_client.patch("/settings/checkin", json={"interval_days": 30, "grace_period_days": 7})
        cfg.demo_mode = prev


# ═════════════════════════════════════════════════════════════════════════════
# B-lifecycle — full demo cycle drives a real release trigger
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_demo_lifecycle_minute_grace_expiry_creates_trigger():
    """1-minute grace period, dispatched 2 minutes ago -> _check_grace_periods()
    (the real production task, unmodified) must open a release trigger, exactly
    as it does for the day-based path in test_12's test_b2, but using minutes.
    """
    u = await _create_local_user(
        interval_days=30,       # day columns still populated (never NULL) —
        grace_period_days=7,    # they're the fallback if overrides are cleared.
        last_dispatched_at=NOW() - timedelta(minutes=2),
    )
    await _set_schedule(
        u["schedule_id"],
        check_interval_minutes=1,
        grace_period_minutes=1,
    )

    await _check_grace_periods()
    assert await _trigger_count(u["user_id"]) == 1, (
        "B-lifecycle: minute-based grace_period_minutes did not drive a real trigger"
    )

    # Confirm the day-based columns were untouched by the minute override —
    # they're the documented fallback, not migrated/mutated.
    schedule = await _get_schedule(u["schedule_id"])
    assert schedule.interval_days == 30
    assert schedule.grace_period_days == 7


@pytest.mark.asyncio
async def test_demo_lifecycle_not_yet_expired_no_trigger():
    """Sanity check on the same minute-based path: grace not yet elapsed
    (dispatched 30 seconds ago, 1-minute grace) must NOT trigger."""
    u = await _create_local_user(
        interval_days=30,
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(seconds=30),
    )
    await _set_schedule(
        u["schedule_id"],
        check_interval_minutes=1,
        grace_period_minutes=1,
    )

    await _check_grace_periods()
    assert await _trigger_count(u["user_id"]) == 0, (
        "B-lifecycle regression: trigger fired before the 1-minute grace elapsed"
    )


# ═════════════════════════════════════════════════════════════════════════════
# B-lifecycle (extension) — emergency_confirm_minutes drives the
# pending_confirmation -> processing promotion in minutes, not real 48h
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_demo_lifecycle_emergency_confirm_minutes_sets_short_deliver_after():
    """Mirrors test_b8_emergency_contact_creates_pending_confirmation, but with
    emergency_confirm_minutes set: deliver_after must land minutes out, not
    ~48h out — this is the exact gap that blocked a full live-demo rehearsal
    when an emergency contact is configured."""
    u = await _create_local_user(
        interval_days=30,
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(minutes=2),
    )
    await _set_schedule(
        u["schedule_id"],
        check_interval_minutes=1,
        grace_period_minutes=1,
        emergency_confirm_minutes=2,
    )
    await _add_beneficiary(u["user_id"], email=_test_inbox(), emergency=True)

    before = NOW()
    await _check_grace_periods()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.user_id == u["user_id"])
        )).scalar_one()
        assert trigger.status == TriggerStatus.pending_confirmation
        deliver_after = trigger.deliver_after
        if deliver_after.tzinfo is None:
            deliver_after = deliver_after.replace(tzinfo=timezone.utc)
        assert deliver_after < before + timedelta(minutes=3), (
            "B-lifecycle regression: emergency_confirm_minutes did not shorten "
            "deliver_after — still on the real 48h default"
        )


@pytest.mark.asyncio
async def test_demo_lifecycle_emergency_confirm_minutes_promotes_after_window():
    """Full path: once the (minute-scale) window elapses, _process_pending_triggers
    promotes the trigger out of pending_confirmation — same assertion style as
    test_b8_pending_trigger_promotes_after_window, but reached via a real
    minutes-based deliver_after instead of a manually-advanced 48h one."""
    u = await _create_local_user(
        interval_days=30,
        grace_period_days=7,
        last_dispatched_at=NOW() - timedelta(minutes=2),
    )
    await _set_schedule(
        u["schedule_id"],
        check_interval_minutes=1,
        grace_period_minutes=1,
        emergency_confirm_minutes=1,
    )
    await _add_beneficiary(u["user_id"], email=_test_inbox(), emergency=True)

    await _check_grace_periods()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.user_id == u["user_id"])
        )).scalar_one()
        assert trigger.status == TriggerStatus.pending_confirmation
        trigger_id = trigger.id

    # Real time elapse would take ~1 minute; instead of sleeping in the test
    # suite, backdate deliver_after the same way test_b8's "48h elapse" does —
    # the point under test is that the column already holds a short window,
    # not that we're willing to sleep for it.
    from sqlalchemy import update
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(ReleaseTrigger)
            .where(ReleaseTrigger.id == trigger_id)
            .values(deliver_after=NOW() - timedelta(seconds=1))
        )
        await db.commit()

    await _process_pending_triggers()

    async with AsyncSessionLocal() as db:
        trigger = (await db.execute(
            select(ReleaseTrigger).where(ReleaseTrigger.id == trigger_id)
        )).scalar_one()
        assert trigger.status != TriggerStatus.pending_confirmation, (
            "B-lifecycle regression: trigger not promoted after minute-scale window elapsed"
        )
