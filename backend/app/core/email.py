"""
Email sending utilities via Resend.
Provides functions for transactional emails: check-in, delivery, nomination, etc.
"""

import resend
from app.config import get_settings

cfg = get_settings()
resend.api_key = cfg.resend_api_key


def send_checkin_email(
    to: str,
    confirm_url: str,
    snooze_7_url: str,
    snooze_14_url: str,
    snooze_30_url: str,
    snoozes_remaining: int,
) -> str:
    """
    Send the periodic check-in email with confirm and snooze links.
    Returns the Resend message ID.
    TODO: replace inline HTML with a proper template (Jinja2 or similar).
    """
    # TODO: implement email body
    raise NotImplementedError


def send_nomination_email(to: str, nominator_name: str) -> str:
    """
    Send nomination notification to a newly added beneficiary.
    Must not reveal capsule content, count, or account details.
    Returns the Resend message ID.
    TODO: implement email body — legal review required before production use.
    """
    raise NotImplementedError


def send_delivery_email(
    to: str,
    beneficiary_name: str,
    capsules_html: str,
) -> str:
    """
    Send the delivery email to a beneficiary when a trigger fires.
    capsules_html is the pre-rendered HTML of all assigned capsules.
    Returns the Resend message ID.
    TODO: implement email body — legal review of tone required.
    """
    raise NotImplementedError


def send_grace_period_reminder(to: str, days_remaining: int, confirm_url: str) -> str:
    """
    Send escalating reminder during grace period.
    Returns the Resend message ID.
    """
    # TODO: implement email body
    raise NotImplementedError
