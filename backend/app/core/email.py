"""
Email sending utilities via Resend SDK.

All user-supplied strings (names, titles, content) MUST be passed through
html.escape() before interpolation (S3 hardening lands in Phase 5; escaping
is mandatory now per Phase 2 T9.4).

Phase C: every sender is built in two layers —
  1. a pure `_build_*_email(...)` function that returns
     {"subject": str, "html": str, "text": str} with NO side effects (no
     network calls). These are what `backend/scripts/preview_emails.py` and
     `backend/tests/test_email_templates.py` exercise directly.
  2. a thin `send_*` wrapper (same public signature as before Phase C) that
     calls the builder and hands the result to Resend.
Shared chrome (header/card/footer/button) lives in `_base_template` /
`_button` so all seven emails render as one consistent, email-client-safe
design (table layout, inline CSS only — Gmail/Outlook strip <style> blocks
and don't support flexbox).
"""

import html as html_mod
from datetime import datetime

import resend
from app.config import get_settings

# ── Design tokens (mirrors the frontend's Tailwind palette) ─────────────────
_INK = "#0D1117"
_SLATE = "#3D4F6B"
_MUTED = "#6B7280"
_BG = "#F0F2F5"
_BORDER = "#E5E7EB"
_ACCENT_BLUE = "#2563EB"
_ACCENT_AMBER = "#D97706"
_ACCENT_DANGER = "#C0392B"
_ACCENT_NEUTRAL = _SLATE

_FONT = "Helvetica, Arial, sans-serif"


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


def _pluralize(n: int, singular: str, plural: str | None = None) -> str:
    return singular if n == 1 else (plural or f"{singular}s")


# ── C1: shared layout ────────────────────────────────────────────────────────

def _button(label: str, url: str, color: str = _ACCENT_BLUE) -> str:
    """Table-based CTA button (renders in Outlook, unlike a CSS-styled <a>),
    plus a raw-URL fallback line underneath for deliverability and clients
    that strip the button markup.
    """
    return f"""
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 4px 0;">
        <tr>
          <td align="center" bgcolor="{color}" style="border-radius:8px;">
            <a href="{url}" target="_blank" style="display:inline-block;padding:14px 32px;font-family:{_FONT};font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">{label}</a>
          </td>
        </tr>
      </table>
      <p style="font-family:{_FONT};font-size:12px;color:{_MUTED};margin:4px 0 20px 0;word-break:break-all;">
        Or copy and paste this link into your browser: <a href="{url}" style="color:{color};">{url}</a>
      </p>"""


def _base_template(
    *,
    title: str,
    body_html: str,
    accent: str = _ACCENT_BLUE,
    preheader: str = "",
) -> str:
    """Shared table-based, inline-CSS document. `body_html` is the fully
    assembled content for the card (including any CTA button built via
    `_button()`) — callers control placement of the button relative to
    surrounding copy, since several emails have text both before and after it.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{_BG};-webkit-text-size-adjust:100%;">
  <span style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{preheader}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{_BG};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="background-color:{_INK};padding:20px 32px;">
              <span style="font-family:{_FONT};font-size:20px;font-weight:700;color:#ffffff;letter-spacing:0.5px;">Legate</span>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;font-family:{_FONT};color:{_INK};font-size:15px;line-height:1.6;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px;border-top:1px solid {_BORDER};">
              <p style="font-family:{_FONT};font-size:12px;color:{_MUTED};margin:0;">
                Legate &mdash; secure digital estate. This is an automated message; please do not reply.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _heading(text: str, color: str = _INK) -> str:
    return f'<h1 style="font-family:{_FONT};font-size:22px;font-weight:700;color:{color};margin:0 0 16px 0;">{text}</h1>'


def _para(html: str, color: str = _INK) -> str:
    return f'<p style="font-family:{_FONT};font-size:15px;line-height:1.6;color:{color};margin:0 0 16px 0;">{html}</p>'


def _banner(html: str, accent: str) -> str:
    return (
        f'<div style="background-color:{accent}1A;border-left:4px solid {accent};'
        f'padding:14px 16px;margin:0 0 20px 0;border-radius:0 8px 8px 0;">'
        f'<p style="font-family:{_FONT};font-size:14px;color:{_INK};margin:0;font-weight:600;">{html}</p></div>'
    )


# ── 1. Check-in email ────────────────────────────────────────────────────────

def _build_checkin_email(
    confirm_url: str,
    snooze_7_url: str,
    snooze_14_url: str,
    snooze_30_url: str,
    snoozes_remaining: int,
) -> dict:
    remaining_word = _pluralize(snoozes_remaining, "snooze")
    body = "".join([
        _heading("Are you okay?"),
        _para("This is your Legate check-in. Please confirm you&rsquo;re well so your timer resets."),
        _button("Yes, I&rsquo;m okay &#x2714;", confirm_url, _ACCENT_BLUE),
        f'<div style="margin-top:8px;padding-top:16px;border-top:1px solid {_BORDER};">'
        f'<p style="font-family:{_FONT};font-size:13px;color:{_MUTED};margin:0 0 8px 0;">'
        f'Not a good time? Snooze your check-in ({snoozes_remaining} {remaining_word} remaining):</p>'
        f'<p style="font-family:{_FONT};font-size:13px;margin:0;">'
        f'<a href="{snooze_7_url}" style="color:{_ACCENT_BLUE};text-decoration:none;margin-right:16px;">Snooze 7 days</a>'
        f'<a href="{snooze_14_url}" style="color:{_ACCENT_BLUE};text-decoration:none;margin-right:16px;">Snooze 14 days</a>'
        f'<a href="{snooze_30_url}" style="color:{_ACCENT_BLUE};text-decoration:none;">Snooze 30 days</a>'
        f'</p></div>',
        _para("These links expire in 7 days. If you did not expect this email, please ignore it.", _MUTED),
    ])
    html = _base_template(
        title="Legate check-in",
        body_html=body,
        accent=_ACCENT_BLUE,
        preheader="Please confirm you're okay to reset your Legate check-in timer.",
    )
    text = (
        "Are you okay?\n\n"
        "This is your Legate check-in. Please confirm you're well so your timer resets.\n\n"
        f"Confirm: {confirm_url}\n\n"
        f"Not a good time? Snooze your check-in ({snoozes_remaining} {remaining_word} remaining):\n"
        f"  7 days:  {snooze_7_url}\n"
        f"  14 days: {snooze_14_url}\n"
        f"  30 days: {snooze_30_url}\n\n"
        "These links expire in 7 days. If you did not expect this email, please ignore it.\n"
        "Legate - your digital estate, in good hands."
    )
    return {"subject": "Legate check-in: are you okay?", "html": html, "text": text}


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
    built = _build_checkin_email(confirm_url, snooze_7_url, snooze_14_url, snooze_30_url, snoozes_remaining)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 2. Nomination email ──────────────────────────────────────────────────────

def _build_nomination_email(nominator_name: str) -> dict:
    nominator = _esc(nominator_name)
    body = "".join([
        _heading("You&rsquo;ve been added as a Legate beneficiary"),
        _para(
            f"<strong>{nominator}</strong> has named you as a beneficiary on Legate, "
            "a digital estate planning service."
        ),
        _para(
            "Legate allows people to securely store important messages, documents, and personal "
            "letters to be delivered to loved ones in the event of their passing or long-term "
            "incapacitation."
        ),
        _para(
            "You don&rsquo;t need to create an account or take any action right now. If the time "
            "comes, Legate will contact you directly with any messages intended for you."
        ),
        _para(
            "<strong>Legal notice:</strong> This is not a legal will or testament. Legate facilitates "
            "personal message delivery only. For legal estate planning, please consult a qualified "
            "solicitor or attorney.",
            _MUTED,
        ),
    ])
    html = _base_template(
        title="You&rsquo;ve been added as a Legate beneficiary",
        body_html=body,
        accent=_ACCENT_BLUE,
        preheader=f"{nominator} has named you as a beneficiary on Legate.",
    )
    text = (
        "You've been added as a Legate beneficiary\n\n"
        f"{nominator_name} has named you as a beneficiary on Legate, a digital estate planning service.\n\n"
        "Legate allows people to securely store important messages, documents, and personal letters "
        "to be delivered to loved ones in the event of their passing or long-term incapacitation.\n\n"
        "You don't need to create an account or take any action right now. If the time comes, Legate "
        "will contact you directly with any messages intended for you.\n\n"
        "Legal notice: This is not a legal will or testament. Legate facilitates personal message "
        "delivery only. For legal estate planning, please consult a qualified solicitor or attorney.\n\n"
        "Legate - your digital estate, in good hands."
    )
    return {"subject": "You've been added as a Legate beneficiary", "html": html, "text": text}


def send_nomination_email(to: str, nominator_name: str) -> str:
    r = _get_resend()
    cfg = get_settings()
    built = _build_nomination_email(nominator_name)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 3. Delivery email ────────────────────────────────────────────────────────

def _build_delivery_email(beneficiary_name: str, capsules_html: str, nominator_name: str = "someone") -> dict:
    """capsules_html is pre-rendered and pre-sanitized by the delivery task
    (see backend/app/worker/tasks/delivery_tasks.py::_build_capsule_html);
    names are escaped here.
    """
    beneficiary = _esc(beneficiary_name)
    nominator = _esc(nominator_name)
    body = "".join([
        _heading(f"A message for you from {nominator}"),
        f'<div style="background-color:{_ACCENT_BLUE}1A;border-left:4px solid {_ACCENT_BLUE};'
        f'padding:16px;margin:0 0 28px 0;border-radius:0 8px 8px 0;">'
        f'<p style="font-family:{_FONT};font-size:15px;color:{_INK};margin:0 0 8px 0;">Dear {beneficiary},</p>'
        f'<p style="font-family:{_FONT};font-size:15px;color:{_INK};margin:0;">'
        f'{nominator} prepared the following message(s) for you through Legate, a secure digital estate '
        f'service. These messages were meant to reach you only at this moment.</p></div>',
        capsules_html,
        _para(
            "Legate is a private digital estate service. These messages were prepared in advance and "
            "delivered automatically according to the sender&rsquo;s instructions.",
            _MUTED,
        ),
    ])
    html = _base_template(
        title="A message for you",
        body_html=body,
        accent=_ACCENT_BLUE,
        preheader=f"{nominator} prepared a message for you through Legate.",
    )
    text = (
        f"A message for you from {nominator_name}\n\n"
        f"Dear {beneficiary_name},\n\n"
        f"{nominator_name} prepared message(s) for you through Legate, a secure digital estate service. "
        "These messages were meant to reach you only at this moment.\n\n"
        "Open this email in an HTML-capable mail client to view the full message(s) and any attached photos or videos.\n\n"
        "Legate is a private digital estate service. These messages were prepared in advance and delivered "
        "automatically according to the sender's instructions.\n\n"
        "Legate - your digital estate, in good hands."
    )
    return {"subject": f"A message for you from {_strip_header(nominator_name)}", "html": html, "text": text}


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
    built = _build_delivery_email(beneficiary_name, capsules_html, nominator_name)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 4. Grace period reminder (urgent — amber) ────────────────────────────────

def _build_grace_period_reminder_email(days_remaining: int, confirm_url: str) -> dict:
    day_word = _pluralize(days_remaining, "day")
    body = "".join([
        _banner(f"&#x26A0; Action required &mdash; {days_remaining} {day_word} remaining", _ACCENT_AMBER),
        _heading("Your Legate check-in is overdue", _ACCENT_AMBER),
        _para(
            "We haven&rsquo;t received a check-in confirmation from you. You have "
            f"<strong>{days_remaining} {day_word}</strong> remaining before your Legate messages are "
            "automatically delivered to your designated beneficiaries."
        ),
        _para("If you are well, please confirm now:"),
        _button("I&rsquo;m okay &mdash; reset my timer &#x2714;", confirm_url, _ACCENT_AMBER),
        _para(
            "If you are unable to confirm and this action would be a mistake, please contact someone "
            "you trust to use your emergency pause link.",
            _MUTED,
        ),
    ])
    html = _base_template(
        title="Legate: action required",
        body_html=body,
        accent=_ACCENT_AMBER,
        preheader=f"{days_remaining} {day_word} remaining before your Legate messages are delivered.",
    )
    text = (
        f"Action required - {days_remaining} {day_word} remaining\n\n"
        "Your Legate check-in is overdue.\n\n"
        "We haven't received a check-in confirmation from you. You have "
        f"{days_remaining} {day_word} remaining before your Legate messages are automatically delivered "
        "to your designated beneficiaries.\n\n"
        f"Confirm you're okay: {confirm_url}\n\n"
        "If you are unable to confirm and this action would be a mistake, please contact someone you "
        "trust to use your emergency pause link.\n\n"
        "Legate - your digital estate, in good hands."
    )
    return {
        "subject": f"Legate: action required — {days_remaining} days remaining",
        "html": html,
        "text": text,
    }


def send_grace_period_reminder(to: str, days_remaining: int, confirm_url: str) -> str:
    r = _get_resend()
    cfg = get_settings()
    built = _build_grace_period_reminder_email(days_remaining, confirm_url)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 5. Emergency pause (urgent — amber) ──────────────────────────────────────

def _build_emergency_pause_email(contact_name: str, user_name: str, pause_url: str, deadline: datetime) -> dict:
    """
    FR-23/24: notify the emergency contact that delivery is about to proceed,
    with a single-click pause link valid until the 48h deadline.
    Plain-language, non-alarming tone per FR-40.
    """
    contact = _esc(contact_name)
    user = _esc(user_name)
    deadline_str = deadline.strftime("%A, %B %d, %Y at %H:%M UTC")
    body = "".join([
        _heading(f"Hello {contact},"),
        _para(
            f"<strong>{user}</strong> named you as their emergency contact on Legate, a service that "
            "stores personal messages to be delivered to loved ones if something happens to them."
        ),
        _banner(
            f"{user} has not responded to their regular check-in messages. If we don&rsquo;t hear "
            f"anything, their stored messages will be delivered to their chosen recipients after "
            f"{deadline_str}.",
            _ACCENT_AMBER,
        ),
        _para(
            f"If you know that {user} is okay &mdash; for example, they are travelling, unwell but "
            "recovering, or simply unable to reach their email &mdash; you can pause this delivery for "
            "7 days with one click:"
        ),
        _button("Pause delivery for 7 days", pause_url, _ACCENT_AMBER),
        _para("If you believe the delivery should proceed, no action is needed.", _MUTED),
        _para(
            "This link can be used once and expires at the deadline above. If you weren&rsquo;t "
            "expecting this email, you can safely ignore it.",
            _MUTED,
        ),
    ])
    html = _base_template(
        title="Legate needs your help",
        body_html=body,
        accent=_ACCENT_AMBER,
        preheader=f"{user} hasn't checked in — you can pause delivery for 7 days.",
    )
    text = (
        f"Hello {contact_name},\n\n"
        f"{user_name} named you as their emergency contact on Legate, a service that stores personal "
        "messages to be delivered to loved ones if something happens to them.\n\n"
        f"{user_name} has not responded to their regular check-in messages. If we don't hear anything, "
        f"their stored messages will be delivered to their chosen recipients after {deadline_str}.\n\n"
        f"If you know that {user_name} is okay, you can pause this delivery for 7 days: {pause_url}\n\n"
        "If you believe the delivery should proceed, no action is needed.\n\n"
        "This link can be used once and expires at the deadline above. If you weren't expecting this "
        "email, you can safely ignore it.\n\n"
        "Legate - your digital estate, in good hands."
    )
    return {
        "subject": f"Legate: {_strip_header(user_name)} hasn't checked in — you can pause delivery",
        "html": html,
        "text": text,
    }


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
    built = _build_emergency_pause_email(contact_name, user_name, pause_url, deadline)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 6. Beneficiary removal (neutral) ─────────────────────────────────────────

def _build_beneficiary_removal_email(beneficiary_name: str) -> dict:
    """
    FR-22: neutral removal notification. Mirrors FR-20 constraints — no
    account details, no content details, no reason given.
    """
    beneficiary = _esc(beneficiary_name)
    body = "".join([
        _heading("Legate beneficiary update", _SLATE),
        _para(f"Dear {beneficiary},"),
        _para("You are no longer listed as a beneficiary on a Legate account. No action is required on your part."),
        _para("If you have questions, please reach out to the person who originally added you.", _MUTED),
    ])
    html = _base_template(
        title="Legate beneficiary update",
        body_html=body,
        accent=_ACCENT_NEUTRAL,
        preheader="You are no longer listed as a beneficiary on a Legate account.",
    )
    text = (
        "Legate beneficiary update\n\n"
        f"Dear {beneficiary_name},\n\n"
        "You are no longer listed as a beneficiary on a Legate account. No action is required on your part.\n\n"
        "If you have questions, please reach out to the person who originally added you.\n\n"
        "Legate - your digital estate, in good hands."
    )
    return {"subject": "Legate beneficiary update", "html": html, "text": text}


def send_beneficiary_removal_email(to: str, beneficiary_name: str) -> str:
    """
    FR-22: neutral removal notification. Mirrors FR-20 constraints — no
    account details, no content details, no reason given.
    """
    r = _get_resend()
    cfg = get_settings()
    built = _build_beneficiary_removal_email(beneficiary_name)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")


# ── 7. Internal alert (ops only — minimal styling) ───────────────────────────

def _build_alert_email(subject: str, body_text: str) -> dict:
    """Internal operational alert (B6: permanent delivery failure)."""
    subject_esc = _esc(subject)
    body_html_escaped = _esc(body_text).replace("\n", "<br>")
    body = "".join([
        _heading(f"&#x1F6A8; {subject_esc}", _ACCENT_DANGER),
        f'<pre style="font-family:Menlo,Consolas,monospace;font-size:13px;white-space:pre-wrap;'
        f'word-break:break-word;color:{_INK};background-color:#F9FAFB;border:1px solid {_BORDER};'
        f'border-radius:8px;padding:12px;margin:0;">{body_html_escaped}</pre>',
    ])
    html = _base_template(
        title=subject_esc,
        body_html=body,
        accent=_ACCENT_DANGER,
        preheader="Internal Legate operational alert.",
    )
    text = f"{subject}\n\n{body_text}"
    return {"subject": f"[LEGATE ALERT] {_strip_header(subject)}", "html": html, "text": text}


def send_alert_email(to: str, subject: str, body_text: str) -> str:
    """Internal operational alert (B6: permanent delivery failure)."""
    r = _get_resend()
    cfg = get_settings()
    built = _build_alert_email(subject, body_text)
    data = r.Emails.send({
        "from": cfg.email_from,
        "to": [to],
        "subject": built["subject"],
        "html": built["html"],
        "text": built["text"],
    })
    return data.get("id", "")
