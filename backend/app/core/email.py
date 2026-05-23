"""
Email sending utilities via Resend SDK.
"""

import resend
from app.config import get_settings


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
    r = _get_resend()
    cfg = get_settings()
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
  <h2>A message for you from {nominator_name}</h2>
  <div class="intro">
    <p>Dear {beneficiary_name},</p>
    <p>{nominator_name} prepared the following message(s) for you through Legate, a secure digital estate service. These messages were meant to reach you only at this moment.</p>
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
        "subject": f"A message for you from {nominator_name}",
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
