"""
Phase B: schedule-math helpers.

Every place that computes a check-in interval or grace-period timedelta from
a CheckInSchedule row must go through these two functions instead of calling
timedelta(days=...) directly. That's what lets a demo-mode minute override
(check_interval_minutes / grace_period_minutes) take precedence without
touching the day-based columns or their math anywhere else.

Normal-mode behavior (both minute columns NULL) is byte-for-byte identical
to before Phase B: these just return timedelta(days=schedule.*_days).
"""

from datetime import timedelta

# FR-23: hours an emergency contact has to pause delivery before a
# pending_confirmation trigger promotes to processing, when no demo-mode
# minute override is set. Lives here (not checkin_tasks.py) so both the
# worker task and emergency_confirm_delta() below share one source of truth.
EMERGENCY_CONFIRMATION_WINDOW_HOURS = 48


def interval_delta(schedule) -> timedelta:
    """Time between check-ins. Minute override (demo mode) takes precedence
    over interval_days when set."""
    if schedule.check_interval_minutes:
        return timedelta(minutes=schedule.check_interval_minutes)
    return timedelta(days=schedule.interval_days)


def grace_delta(schedule) -> timedelta:
    """Grace window after a missed check-in. Minute override (demo mode)
    takes precedence over grace_period_days when set."""
    if schedule.grace_period_minutes:
        return timedelta(minutes=schedule.grace_period_minutes)
    return timedelta(days=schedule.grace_period_days)


def emergency_confirm_delta(schedule) -> timedelta:
    """FR-23 emergency-contact confirmation window. Minute override (demo
    mode) takes precedence over the 48h default when set — otherwise a demo
    account with an emergency contact configured could never finish a live
    rehearsal of the missed-checkin -> release -> delivery lifecycle within
    the same minutes-scale demo used for the base interval/grace period."""
    if schedule.emergency_confirm_minutes:
        return timedelta(minutes=schedule.emergency_confirm_minutes)
    return timedelta(hours=EMERGENCY_CONFIRMATION_WINDOW_HOURS)
