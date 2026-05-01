"""Pydantic schemas for check-in settings endpoints."""

from datetime import datetime
from pydantic import BaseModel


class CheckInSettingsUpdate(BaseModel):
    interval_days: int | None = None
    grace_period_days: int | None = None


class CheckInSettingsResponse(BaseModel):
    interval_days: int
    grace_period_days: int
    next_dispatch_at: datetime | None
    last_confirmed_at: datetime | None
    snooze_count: int
    snooze_limit: int

    model_config = {"from_attributes": True}
