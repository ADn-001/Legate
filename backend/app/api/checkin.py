"""
Check-in token redemption routes.
Unauthenticated — accessed directly from email links.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.checkin_service import CheckInService

router = APIRouter()

_CONFIRMED_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Legate — Confirmed</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:80px auto;text-align:center;color:#1a1a1a}}
h1{{color:#2e7d32}}p{{color:#555}}</style></head>
<body><h1>&#x2714; You&rsquo;re confirmed</h1>
<p>Your Legate timer has been reset. We&rsquo;ll check in with you again in {days} days.</p>
<p style="font-size:.85em;color:#999">You can close this tab.</p></body></html>"""

_SNOOZED_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Legate — Snoozed</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:80px auto;text-align:center;color:#1a1a1a}}
h1{{color:#1565c0}}p{{color:#555}}</style></head>
<body><h1>&#x23F3; Snoozed for {days} days</h1>
<p>Your check-in has been postponed. We&rsquo;ll follow up again in {days} days.</p>
<p style="font-size:.85em;color:#999">You can close this tab.</p></body></html>"""

_PAUSED_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Legate — Paused</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:80px auto;text-align:center;color:#1a1a1a}}
h1{{color:#e65100}}p{{color:#555}}</style></head>
<body><h1>&#x23F8; Timer paused</h1>
<p>The Legate delivery timer has been paused for 7 days.</p>
<p style="font-size:.85em;color:#999">You can close this tab.</p></body></html>"""

_ERROR_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Legate — Error</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:80px auto;text-align:center;color:#1a1a1a}}
h1{{color:#c62828}}p{{color:#555}}</style></head>
<body><h1>&#x26A0; {title}</h1><p>{message}</p></body></html>"""


def _error_page(title: str, message: str, status_code: int = 400) -> HTMLResponse:
    return HTMLResponse(
        content=_ERROR_HTML.format(title=title, message=message),
        status_code=status_code,
    )


@router.get("/confirm")
async def confirm_checkin(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    try:
        svc = CheckInService(db)
        await svc.confirm(token, ip, user_agent)
        return HTMLResponse(content=_CONFIRMED_HTML.format(days=30), status_code=200)
    except Exception as exc:
        code = getattr(exc, "status_code", 400)
        detail = getattr(exc, "detail", str(exc))
        return _error_page("Could not confirm", detail, code)


@router.get("/snooze")
async def snooze_checkin(
    token: str,
    days: int,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        svc = CheckInService(db)
        await svc.snooze(token, days)
        return HTMLResponse(content=_SNOOZED_HTML.format(days=days), status_code=200)
    except Exception as exc:
        code = getattr(exc, "status_code", 400)
        detail = getattr(exc, "detail", str(exc))
        return _error_page("Could not snooze", detail, code)


@router.get("/emergency/pause")
async def emergency_pause(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        svc = CheckInService(db)
        await svc.emergency_pause(token)
        return HTMLResponse(content=_PAUSED_HTML, status_code=200)
    except Exception as exc:
        code = getattr(exc, "status_code", 400)
        detail = getattr(exc, "detail", str(exc))
        return _error_page("Could not pause", detail, code)
