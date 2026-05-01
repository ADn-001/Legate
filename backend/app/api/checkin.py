"""
Check-in token redemption routes.
These endpoints are intentionally unauthenticated — they are accessed
directly from email links without requiring app login.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/confirm")
async def confirm_checkin(token: str, request: Request):
    """
    Validate and consume a check-in confirmation token.
    Resets the check-in timer and returns an HTML confirmation page.
    Single-use. Expires 7 days after dispatch.
    """
    # TODO: look up token in checkin_events, validate, mark used
    # TODO: update checkin_schedule last_confirmed_at + next_dispatch_at
    # TODO: return styled HTML confirmation page
    raise NotImplementedError


@router.get("/snooze")
async def snooze_checkin(token: str, days: int, request: Request):
    """
    Validate and consume a snooze token.
    Extends next_dispatch_at by the specified number of days.
    Enforces snooze_limit per cycle.
    """
    # TODO: validate token, check snooze_count < snooze_limit
    # TODO: update schedule, increment snooze_count
    raise NotImplementedError


@router.get("/emergency/pause")
async def emergency_pause(token: str, request: Request):
    """
    Emergency contact pause action.
    Extends grace period by 7 days. Maximum 2 pauses per trigger event.
    """
    # TODO: validate token, check pause_count < 2
    # TODO: update release_trigger + checkin_schedule
    raise NotImplementedError
