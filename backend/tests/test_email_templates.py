"""
Phase C: tests for the pure `_build_*_email` template builders in
app/core/email.py. These do no network I/O (no Resend calls), so they run as
plain unit tests — no DB, no e2e fixtures, no Docker dependency beyond the
api container's Python environment.
"""

from datetime import datetime, timedelta, timezone

from app.core.email import (
    _build_checkin_email,
    _build_nomination_email,
    _build_delivery_email,
    _build_grace_period_reminder_email,
    _build_emergency_pause_email,
    _build_beneficiary_removal_email,
    _build_alert_email,
)

XSS_NAME = "Alex <script>alert(1)</script> Rivera"
XSS_ESCAPED = "Alex &lt;script&gt;alert(1)&lt;/script&gt; Rivera"


def _assert_well_formed(built: dict):
    """Common shape + f-string-leftover checks for every builder's output."""
    assert set(built.keys()) >= {"subject", "html", "text"}
    assert built["subject"]
    assert built["html"].strip().startswith("<!DOCTYPE html>")
    assert built["text"].strip()
    # No unformatted f-string braces should ever reach the rendered output —
    # none of the templates use literal `{`/`}` (no embedded <style> blocks,
    # no JSON), so any brace present indicates a formatting bug.
    assert "{" not in built["html"]
    assert "}" not in built["html"]


# ---------------------------------------------------------------------------
# Check-in email (has a CTA + three snooze links)
# ---------------------------------------------------------------------------

def test_checkin_email_well_formed():
    built = _build_checkin_email(
        confirm_url="https://legate.test/confirm?token=abc",
        snooze_7_url="https://legate.test/snooze?d=7",
        snooze_14_url="https://legate.test/snooze?d=14",
        snooze_30_url="https://legate.test/snooze?d=30",
        snoozes_remaining=2,
    )
    _assert_well_formed(built)


def test_checkin_email_cta_present_in_html_and_text():
    built = _build_checkin_email(
        confirm_url="https://legate.test/confirm?token=abc",
        snooze_7_url="https://legate.test/snooze?d=7",
        snooze_14_url="https://legate.test/snooze?d=14",
        snooze_30_url="https://legate.test/snooze?d=30",
        snoozes_remaining=1,
    )
    assert "https://legate.test/confirm?token=abc" in built["html"]
    assert "https://legate.test/confirm?token=abc" in built["text"]
    assert "https://legate.test/snooze?d=7" in built["html"]
    assert "https://legate.test/snooze?d=14" in built["html"]
    assert "https://legate.test/snooze?d=30" in built["html"]
    # singular "snooze" when exactly 1 remaining
    assert "1 snooze remaining" in built["html"]


def test_checkin_email_plural_snoozes_remaining():
    built = _build_checkin_email(
        confirm_url="https://legate.test/confirm",
        snooze_7_url="https://legate.test/s7",
        snooze_14_url="https://legate.test/s14",
        snooze_30_url="https://legate.test/s30",
        snoozes_remaining=3,
    )
    assert "3 snoozes remaining" in built["html"]


# ---------------------------------------------------------------------------
# Nomination email (no CTA)
# ---------------------------------------------------------------------------

def test_nomination_email_well_formed():
    built = _build_nomination_email(nominator_name="Alex Rivera")
    _assert_well_formed(built)
    assert "Alex Rivera" in built["html"]
    assert "beneficiary" in built["html"].lower()


def test_nomination_email_escapes_script_in_name():
    built = _build_nomination_email(nominator_name=XSS_NAME)
    assert "<script>" not in built["html"]
    assert XSS_ESCAPED in built["html"]


# ---------------------------------------------------------------------------
# Delivery email (no CTA; embeds pre-rendered capsules_html)
# ---------------------------------------------------------------------------

def test_delivery_email_well_formed():
    built = _build_delivery_email(
        beneficiary_name="Jordan Rivera",
        capsules_html="<div>sample capsule content</div>",
        nominator_name="Alex Rivera",
    )
    _assert_well_formed(built)
    assert "sample capsule content" in built["html"]


def test_delivery_email_escapes_names():
    built = _build_delivery_email(
        beneficiary_name=XSS_NAME,
        capsules_html="<div>content</div>",
        nominator_name=XSS_NAME,
    )
    assert "<script>" not in built["html"]
    assert XSS_ESCAPED in built["html"]
    # subject header injection defense is CRLF-stripping only (_strip_header),
    # not HTML-escaping — a subject line isn't rendered as HTML by mail
    # clients, so this only needs to guard against header injection.
    assert "\n" not in built["subject"] and "\r" not in built["subject"]


def test_delivery_email_default_nominator():
    built = _build_delivery_email(beneficiary_name="Jordan", capsules_html="<div>x</div>")
    assert "someone" in built["html"]


# ---------------------------------------------------------------------------
# Grace period reminder (urgent, amber; has a CTA)
# ---------------------------------------------------------------------------

def test_grace_period_reminder_well_formed():
    built = _build_grace_period_reminder_email(days_remaining=3, confirm_url="https://legate.test/confirm")
    _assert_well_formed(built)


def test_grace_period_reminder_cta_present_and_day_wording():
    built = _build_grace_period_reminder_email(days_remaining=1, confirm_url="https://legate.test/confirm?x=1")
    assert "https://legate.test/confirm?x=1" in built["html"]
    assert "https://legate.test/confirm?x=1" in built["text"]
    assert "1 day" in built["html"]
    assert "1 days" not in built["html"]

    built_plural = _build_grace_period_reminder_email(days_remaining=5, confirm_url="https://legate.test/c")
    assert "5 days" in built_plural["html"]
    assert "5 days remaining" in built_plural["subject"]


# ---------------------------------------------------------------------------
# Emergency pause (urgent, amber; has a CTA)
# ---------------------------------------------------------------------------

def test_emergency_pause_email_well_formed():
    built = _build_emergency_pause_email(
        contact_name="Sam Okafor",
        user_name="Alex Rivera",
        pause_url="https://legate.test/pause?token=abc",
        deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    _assert_well_formed(built)
    assert "https://legate.test/pause?token=abc" in built["html"]
    assert "https://legate.test/pause?token=abc" in built["text"]


def test_emergency_pause_email_escapes_names_and_strips_subject_header():
    built = _build_emergency_pause_email(
        contact_name=XSS_NAME,
        user_name=XSS_NAME,
        pause_url="https://legate.test/pause",
        deadline=datetime.now(timezone.utc),
    )
    assert "<script>" not in built["html"]
    assert XSS_ESCAPED in built["html"]
    # same CRLF-only guarantee as the delivery email subject — see comment above.
    assert "\n" not in built["subject"] and "\r" not in built["subject"]


# ---------------------------------------------------------------------------
# Beneficiary removal (neutral, no CTA)
# ---------------------------------------------------------------------------

def test_beneficiary_removal_email_well_formed():
    built = _build_beneficiary_removal_email(beneficiary_name="Jordan Rivera")
    _assert_well_formed(built)
    assert "Jordan Rivera" in built["html"]
    # FR-20/22: neutral copy — no account/content details.
    assert "content" not in built["html"].lower()


def test_beneficiary_removal_email_escapes_name():
    built = _build_beneficiary_removal_email(beneficiary_name=XSS_NAME)
    assert "<script>" not in built["html"]
    assert XSS_ESCAPED in built["html"]


# ---------------------------------------------------------------------------
# Internal alert (ops only; escaped body + subject header-stripped)
# ---------------------------------------------------------------------------

def test_alert_email_well_formed():
    built = _build_alert_email(subject="Delivery failed", body_text="Trigger: abc\nUser: xyz")
    _assert_well_formed(built)
    assert built["subject"].startswith("[LEGATE ALERT]")
    assert "Trigger: abc" in built["html"]


def test_alert_email_escapes_subject_and_body():
    built = _build_alert_email(subject=XSS_NAME, body_text=f"reason: {XSS_NAME}")
    assert "<script>" not in built["html"]
    assert XSS_ESCAPED in built["html"]
    # subject header is stripped of CR/LF, not HTML-escaped (it's a header, not HTML)
    assert "\n" not in built["subject"] and "\r" not in built["subject"]
