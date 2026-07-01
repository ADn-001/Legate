"""
Email sending utilities via Resend SDK.

All user-supplied strings (names, titles, content) MUST be passed through
html.escape() before interpolation (S3 hardening lands in Phase 5; escaping
is mandatory now per Phase 2 T9.4).
"""

import html as html_mod
from datetime import datetime

import resend
from app.config import get_settings


def _esc(value: str | None) -> str:
    """HTML-escape a value for safe interpolation into HTML templates."""
    return html_mod.escape(value or "", quote=True)


def _strip_header(value: str | None) -> str:
    """Strip CR and LF from a string to prevent email header injection.
    Use this for any user-supplied fragment that appears in a Subject or other
    header (not the HTML body — use _esc for body content).
    """
    return (value or "").replace("\r", "").replace("\n", "").replace("\x00", "")


def _get_resend():
    cfg = get_settings()
    resend.api_key = cfg.resend_api_key
    return resend


def send_checkin_email(
    to: str,
    confirm_url: str,
    snooze_7_url: str,
    snooze_14_url: str,
    snooze_30_url: str,
    snoozes_remaining: int,
) -> str:
    r = _get_resend()
    cfg = get_settings()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Legate check-in</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .btn{{display:inline-block;padding:14px 28px;background:#2e7d32;color:#fff!important;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600;margin:16px 0}}
  .snooze-links{{margin-top:24px;padding-top:16px;border-top:1px solid #eee}}
  .snooze-links a{{color:#555;margin-right:16px;font-size:14px}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <h2>Are you okay?</h2>
  <p>This is your Legate check-in. Please confirm you&rsquo;re well so your timer resets.</p>
  <a class="btn" href="{confirm_url}">Yes, I&rsquo;m okay &#x2714;</a>
  <div class="snooze-links">
    <p>Not a good time? Snooze your check-in ({snoozes_remaining} snooze{"s" if snoozes_remaining != 1 else ""} remaining):</p>
    <a href="{snooze_7_url}">Snooze 7 days</a>
    <a href="{snooze_14_url}">Snooze 14 days</a>
    <a href="{snooze_30_url}">Snooze 30 days</a>
  </div>
  <div class="footer">
    <p>These links expire in 7 days. If you did not expect this email, please ignore it.</p>
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": "Legate check-in: are you okay?",
        "html": html,
    })
    return data.get("id", "")


def send_nomination_email(to: str, nominator_name: str) -> str:
    r = _get_resend()
    cfg = get_settings()
    nominator_name = _esc(nominator_name)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>You&rsquo;ve been added as a Legate beneficiary</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <h2>You&rsquo;ve been added as a Legate beneficiary</h2>
  <p><strong>{nominator_name}</strong> has named you as a beneficiary on Legate, a digital estate planning service.</p>
  <p>Legate allows people to securely store important messages, documents, and personal letters to be delivered to loved ones in the event of their passing or long-term incapacitation.</p>
  <p>You don&rsquo;t need to create an account or take any action right now. If the time comes, Legate will contact you directly with any messages intended for you.</p>
  <div class="footer">
    <p><strong>Legal notice:</strong> This is not a legal will or testament. Legate facilitates personal message delivery only. For legal estate planning, please consult a qualified solicitor or attorney.</p>
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": "You've been added as a Legate beneficiary",
        "html": html,
    })
    return data.get("id", "")


def send_delivery_email(
    to: str,
    beneficiary_name: str,
    capsules_html: str,
    nominator_name: str = "someone",
) -> str:
    """One email per beneficiary (FR-39). capsules_html is pre-rendered and
    pre-sanitized by the delivery task; names are escaped here.

    S3: beneficiary_name and nominator_name are HTML-escaped for the body.
    The subject uses _strip_header (plain text, no HTML entities) to prevent
    header injection.
    """
    r = _get_resend()
    cfg = get_settings()
    # Subject: strip CR/LF only — subjects must not contain HTML entities.
    subject_nominator = _strip_header(nominator_name)
    # Body: full HTML-escaping for safe interpolation into HTML templates.
    beneficiary_name_html = _esc(beneficiary_name)
    nominator_name_html = _esc(nominator_name)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>A message for you</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .intro{{background:#f9f9f9;border-left:4px solid #2e7d32;padding:16px;margin-bottom:32px;border-radius:0 6px 6px 0}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <h2>A message for you from {nominator_name_html}</h2>
  <div class="intro">
    <p>Dear {beneficiary_name_html},</p>
    <p>{nominator_name_html} prepared the following message(s) for you through Legate, a secure digital estate service. These messages were meant to reach you only at this moment.</p>
  </div>
  {capsules_html}
  <div class="footer">
    <p>Legate is a private digital estate service. These messages were prepared in advance and delivered automatically according to the sender&rsquo;s instructions.</p>
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": f"A message for you from {subject_nominator}",
        "html": html,
    })
    return data.get("id", "")


def send_grace_period_reminder(to: str, days_remaining: int, confirm_url: str) -> str:
    r = _get_resend()
    cfg = get_settings()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Legate: action required</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .alert{{background:#fff3e0;border-left:4px solid #e65100;padding:16px;margin-bottom:24px;border-radius:0 6px 6px 0}}
  .btn{{display:inline-block;padding:14px 28px;background:#c62828;color:#fff!important;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600;margin:16px 0}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <div class="alert">
    <strong>&#x26A0; Action required &mdash; {days_remaining} day{"s" if days_remaining != 1 else ""} remaining</strong>
  </div>
  <h2>Your Legate check-in is overdue</h2>
  <p>We haven&rsquo;t received a check-in confirmation from you. You have <strong>{days_remaining} day{"s" if days_remaining != 1 else ""}</strong> remaining before your Legate messages are automatically delivered to your designated beneficiaries.</p>
  <p>If you are well, please confirm now:</p>
  <a class="btn" href="{confirm_url}">I&rsquo;m okay &mdash; reset my timer &#x2714;</a>
  <p>If you are unable to confirm and this action would be a mistake, please contact someone you trust to use your emergency pause link.</p>
  <div class="footer">
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": f"Legate: action required — {days_remaining} days remaining",
        "html": html,
    })
    return data.get("id", "")


def send_emergency_pause_email(
    to: str,
    contact_name: str,
    user_name: str,
    pause_url: str,
    deadline: datetime,
) -> str:
    """
    FR-23/24: notify the emergency contact that delivery is about to proceed,
    with a single-click pause link valid until the 48h deadline.
    Plain-language, non-alarming tone per FR-40.

    S3: user_name and contact_name are HTML-escaped for the body.
    The subject uses _strip_header (no HTML entities) to prevent header injection.
    """
    r = _get_resend()
    cfg = get_settings()
    subject_user = _strip_header(user_name)
    contact_name = _esc(contact_name)
    user_name = _esc(user_name)
    deadline_str = deadline.strftime("%A, %B %d, %Y at %H:%M UTC")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Legate needs your help</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .notice{{background:#fff3e0;border-left:4px solid #e65100;padding:16px;margin-bottom:24px;border-radius:0 6px 6px 0}}
  .btn{{display:inline-block;padding:14px 28px;background:#e65100;color:#fff!important;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600;margin:16px 0}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <h2>Hello {contact_name},</h2>
  <p><strong>{user_name}</strong> named you as their emergency contact on Legate, a service that stores personal messages to be delivered to loved ones if something happens to them.</p>
  <div class="notice">
    <p>{user_name} has not responded to their regular check-in messages. If we don&rsquo;t hear anything, their stored messages will be delivered to their chosen recipients after <strong>{deadline_str}</strong>.</p>
  </div>
  <p>If you know that {user_name} is okay &mdash; for example, they are travelling, unwell but recovering, or simply unable to reach their email &mdash; you can pause this delivery for 7 days with one click:</p>
  <a class="btn" href="{pause_url}">Pause delivery for 7 days</a>
  <p>If you believe the delivery should proceed, no action is needed.</p>
  <div class="footer">
    <p>This link can be used once and expires at the deadline above. If you weren&rsquo;t expecting this email, you can safely ignore it.</p>
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": f"Legate: {subject_user} hasn't checked in — you can pause delivery",
        "html": html,
    })
    return data.get("id", "")


def send_beneficiary_removal_email(to: str, beneficiary_name: str) -> str:
    """
    FR-22: neutral removal notification. Mirrors FR-20 constraints — no
    account details, no content details, no reason given.
    """
    r = _get_resend()
    cfg = get_settings()
    beneficiary_name = _esc(beneficiary_name)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Legate beneficiary update</title>
<style>
  body{{font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px 16px;color:#1a1a1a}}
  .footer{{margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:16px}}
</style>
</head>
<body>
  <h2>Legate beneficiary update</h2>
  <p>Dear {beneficiary_name},</p>
  <p>You are no longer listed as a beneficiary on a Legate account. No action is required on your part.</p>
  <p>If you have questions, please reach out to the person who originally added you.</p>
  <div class="footer">
    <p>Legate &mdash; your digital estate, in good hands.</p>
  </div>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": "Legate beneficiary update",
        "html": html,
    })
    return data.get("id", "")


def send_alert_email(to: str, subject: str, body_text: str) -> str:
    """Internal operational alert (B6: permanent delivery failure)."""
    r = _get_resend()
    cfg = get_settings()
    subject_safe = _strip_header(subject)
    body_html = _esc(body_text).replace("\n", "<br>")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{_esc(subject)}</title></head>
<body style="font-family:monospace;max-width:700px;margin:0 auto;padding:24px 16px;color:#1a1a1a">
  <h2 style="color:#c62828">&#x1F6A8; {_esc(subject)}</h2>
  <p>{body_html}</p>
</body>
</html>"""

    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": f"[LEGATE ALERT] {subject_safe}",
        "html": html,
    })
    return data.get("id", "")
