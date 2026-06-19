"""Pydantic schemas for check-in settings endpoints."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class CheckInSettingsUpdate(BaseModel):
    # FR-11: interval 7–365 days; FR-12: grace period one of 3/7/14/30.
    interval_days: int | None = Field(None, ge=7, le=365)
    grace_period_days: Literal[3, 7, 14, 30] | None = None


class CheckInSettingsResponse(BaseModel):
    interval_days: int
    grace_period_days: int
    next_dispatch_at: datetime | None
    last_confirmed_at: datetime | None
    snooze_count: int
    snooze_limit: int

    model_config = {"from_attributes": True}
