"""
Test-only helper: mints real Supabase OTPs/tokens via the admin API so
Playwright specs can drive the actual signup-verification and
password-reset flows without reading a real inbox.

This talks to the REAL Supabase project configured by SUPABASE_URL /
SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY. It does not import anything
from `app.*` on purpose — it has no dependency on the FastAPI app, so it
can run standalone with nothing but `pip install supabase`.

NOT shipped in the backend Docker image — see backend/.dockerignore.

Usage:
    python scripts/get_test_otp.py signup-otp <email> <password>
        -> {"otp": "123456"}
        Mints a fresh signup-confirmation OTP for `email` (creating the
        Supabase auth user if `sign_up` hasn't already, or re-minting a
        valid code for an existing unconfirmed user). Verified the same
        way a real "Confirm signup" email code would be, via
        auth.verify_otp(type="email").

    python scripts/get_test_otp.py recovery-tokens <email>
        -> {"access_token": "...", "refresh_token": "..."}
        Mints a password-recovery OTP for `email` and immediately
        exchanges it for a real session, so the caller can drive the
        frontend's /auth/reset-password#access_token=...&refresh_token=...
        link directly.
"""

import json
import os
import sys


def _get(obj, key):
    """Supabase-py response objects are sometimes plain dicts and
    sometimes typed objects depending on client version — handle both."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise SystemExit(
            f"Missing required env var {name}. Set SUPABASE_URL, SUPABASE_ANON_KEY, "
            f"and SUPABASE_SERVICE_ROLE_KEY (same values as backend/.env) before running this script."
        )
    return val


def _admin_client():
    from supabase import create_client
    url = _require_env("SUPABASE_URL")
    service_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, service_key)


def _anon_client():
    from supabase import create_client
    url = _require_env("SUPABASE_URL")
    anon_key = _require_env("SUPABASE_ANON_KEY")
    return create_client(url, anon_key)


def signup_otp(email: str, password: str) -> str:
    sb = _admin_client()
    resp = sb.auth.admin.generate_link({
        "type": "signup",
        "email": email,
        "password": password,
    })
    properties = _get(resp, "properties")
    otp = _get(properties, "email_otp")
    if not otp:
        raise RuntimeError(
            "Supabase admin.generate_link did not return an email_otp. "
            "Check that the project's email templates use the {{ .Token }} "
            "(OTP) variable, not only {{ .ConfirmationURL }}."
        )
    return otp


def recovery_tokens(email: str) -> dict:
    sb_admin = _admin_client()
    resp = sb_admin.auth.admin.generate_link({
        "type": "recovery",
        "email": email,
    })
    properties = _get(resp, "properties")
    otp = _get(properties, "email_otp")
    if not otp:
        raise RuntimeError("Supabase admin.generate_link did not return an email_otp for the recovery link.")

    sb_anon = _anon_client()
    verify = sb_anon.auth.verify_otp({"email": email, "token": otp, "type": "recovery"})
    session = _get(verify, "session")
    if not session:
        raise RuntimeError("Failed to exchange the recovery OTP for a session.")
    return {
        "access_token": _get(session, "access_token"),
        "refresh_token": _get(session, "refresh_token"),
    }


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: _to_jsonable(v) for k, v in vars(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


def debug_link(link_type: str, email: str, password: str | None = None) -> dict:
    """Dumps the full admin.generate_link response so its real field names
    and value shapes can be inspected directly — do not guess further once
    something doesn't look right, run this instead."""
    sb = _admin_client()
    params = {"type": link_type, "email": email}
    if password:
        params["password"] = password
    resp = sb.auth.admin.generate_link(params)
    return _to_jsonable(resp)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "signup-otp":
        if len(sys.argv) != 4:
            raise SystemExit("usage: get_test_otp.py signup-otp <email> <password>")
        print(json.dumps({"otp": signup_otp(sys.argv[2], sys.argv[3])}))
    elif cmd == "recovery-tokens":
        if len(sys.argv) != 3:
            raise SystemExit("usage: get_test_otp.py recovery-tokens <email>")
        print(json.dumps(recovery_tokens(sys.argv[2])))
    elif cmd == "debug-link":
        if len(sys.argv) not in (4, 5):
            raise SystemExit("usage: get_test_otp.py debug-link <signup|recovery> <email> [password]")
        password = sys.argv[4] if len(sys.argv) == 5 else None
        print(json.dumps(debug_link(sys.argv[2], sys.argv[3], password), indent=2, default=str))
    else:
        raise SystemExit(f"Unknown command: {cmd!r}. Expected signup-otp, recovery-tokens, or debug-link.")


if __name__ == "__main__":
    main()
