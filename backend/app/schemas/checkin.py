"""Pydantic schemas for check-in settings endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class CheckInSettingsUpdate(BaseModel):
    # B4/FR-11: interval floor lowered from 7 to 1 day (permanent, all envs).
    interval_days: int | None = Field(None, ge=1, le=365)
    # B4/FR-12: grace period was Literal[3,7,14,30]; now any int 1-30 so the
    # API stops rejecting values outside the frontend's four presets. The
    # frontend keeps offering 3/7/14/30 as quick picks.
    grace_period_days: int | None = Field(None, ge=1, le=30)
    # Phase B demo-mode overrides — writable only when DEMO_MODE=true
    # (enforced in app/api/settings.py, not just here).
    check_interval_minutes: int | None = Field(None, ge=1, le=1440)
    grace_period_minutes: int | None = Field(None, ge=1, le=1440)
    # Phase B (extension): demo-mode override for the FR-23 emergency-contact
    # 48h confirmation window — same gating/writability rules as the two
    # fields above.
    emergency_confirm_minutes: int | None = Field(None, ge=1, le=1440)
    # True clears all minute overrides and recomputes next_dispatch_at from
    # interval_days (returns to normal day-based scheduling).
    clear_minute_overrides: bool = False


class CheckInSettingsResponse(BaseModel):
    interval_days: int
    grace_period_days: int
    # Phase B: NULL means "day-based" (normal mode); non-NULL is the demo
    # override currently in effect.
    check_interval_minutes: int | None = None
    grace_period_minutes: int | None = None
    emergency_confirm_minutes: int | None = None
    next_dispatch_at: datetime | None
    # L3/FR-44: dispatch clears next_dispatch_at, so the dashboard needs
    # last_dispatched_at to detect the "check-in sent, awaiting confirm" state.
    last_dispatched_at: datetime | None = None
    last_confirmed_at: datetime | None
    snooze_count: int
    snooze_limit: int
    # Whether the server has demo mode enabled at all — lets the frontend
    # decide whether to render the demo-scheduling UI.
    demo_mode: bool = False

    model_config = {"from_attributes": True}
