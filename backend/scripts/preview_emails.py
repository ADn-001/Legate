"""
Phase C (C3): render all seven Legate email templates with sample data to
static HTML files, so they can be eyeballed in a browser without sending real
email (and without needing Docker/DB/Supabase access — this only imports the
pure `_build_*` functions from app.core.email, which do no I/O).

Usage (inside the api container, or any environment with the backend
package importable):

    python scripts/preview_emails.py

Writes to scripts/email_previews/*.html. Also doubles as a smoke test that
every builder renders without raising (proves there are no runtime
interpolation errors in the f-string templates).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Make `app` importable when run as `python scripts/preview_emails.py` from
# the backend/ directory (matches how other one-off scripts in this repo are
# invoked, e.g. via `docker compose exec api python scripts/...`).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.email import (  # noqa: E402
    _build_checkin_email,
    _build_nomination_email,
    _build_delivery_email,
    _build_grace_period_reminder_email,
    _build_emergency_pause_email,
    _build_beneficiary_removal_email,
    _build_alert_email,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_previews")


def _sample_capsules_html() -> str:
    """Hand-built sample matching the bordered sub-card markup that
    `app/worker/tasks/delivery_tasks.py::_build_capsule_html` produces, so the
    delivery email preview looks like a real multi-capsule delivery without
    needing a live database, Supabase storage, or decryption key material.
    """
    def card(title: str, body: str, media: str = "") -> str:
        return (
            '<div style="border:1px solid #E5E7EB;border-radius:12px;padding:16px;'
            'margin-bottom:16px;background-color:#ffffff;">'
            f'<h3 style="font-family:Helvetica,Arial,sans-serif;font-size:16px;font-weight:700;'
            f'color:#0D1117;margin:0 0 12px 0;">{title}</h3>'
            f'<div style="font-family:Helvetica,Arial,sans-serif;font-size:14px;'
            f'line-height:1.6;color:#374151;">{body}</div>'
            f'{media}</div>'
        )

    return "".join([
        card(
            "For my daughter, on her wedding day",
            "<p>I always imagined I'd be there to walk you down the aisle. Since I can't, "
            "I wanted to leave you these words instead&hellip;</p>",
            '<div style="margin-top:12px;"><p style="margin:0 0 8px 0;">'
            '<a href="https://example.com/sample-photo" style="color:#2563EB;font-size:13px;">wedding_letter_photo.jpg</a> '
            '<span style="color:#6B7280;font-size:13px;">(download, valid 3 days)</span></p></div>',
        ),
        card(
            "Passwords and account access",
            "<p>Here is where to find the household accounts and how to close them.</p>",
        ),
    ])


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    samples = {
        "checkin": _build_checkin_email(
            confirm_url="https://legate.example.com/checkin/confirm?token=sample",
            snooze_7_url="https://legate.example.com/checkin/snooze?days=7&token=sample",
            snooze_14_url="https://legate.example.com/checkin/snooze?days=14&token=sample",
            snooze_30_url="https://legate.example.com/checkin/snooze?days=30&token=sample",
            snoozes_remaining=2,
        ),
        "nomination": _build_nomination_email(nominator_name="Alex <script>alert(1)</script> Rivera"),
        "delivery": _build_delivery_email(
            beneficiary_name="Jordan Rivera",
            capsules_html=_sample_capsules_html(),
            nominator_name="Alex Rivera",
        ),
        "grace_period_reminder": _build_grace_period_reminder_email(
            days_remaining=3,
            confirm_url="https://legate.example.com/checkin/confirm?token=sample",
        ),
        "emergency_pause": _build_emergency_pause_email(
            contact_name="Sam Okafor",
            user_name="Alex Rivera",
            pause_url="https://legate.example.com/emergency/pause?token=sample",
            deadline=datetime.now(timezone.utc) + timedelta(hours=48),
        ),
        "beneficiary_removal": _build_beneficiary_removal_email(beneficiary_name="Jordan Rivera"),
        "alert": _build_alert_email(
            subject="Delivery failed permanently — trigger sample-trigger-id",
            body_text="Trigger: sample-trigger-id\nUser: sample-user-id\nReason: max retry attempts exceeded",
        ),
    }

    for name, built in samples.items():
        path = os.path.join(OUT_DIR, f"{name}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(built["html"])
        print(f"wrote {path}  (subject: {built['subject']!r})")

    print(f"\n{len(samples)} preview(s) written to {OUT_DIR}")


if __name__ == "__main__":
    main()
