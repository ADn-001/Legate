"""
Pytest fixtures shared across all test modules.

Models are now fully fixed — no sys.modules patches needed.
External services (Supabase, Resend) are mocked so tests run
without live credentials.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

import app.core.supabase as supabase_module
import app.core.email as email_module


def _make_mock_supabase():
    mock = MagicMock()
    # auth stubs
    signup_resp = MagicMock()
    signup_resp.user = MagicMock()
    signup_resp.user.id = "test-supabase-uid"
    mock.auth.sign_up.return_value = signup_resp

    verify_resp = MagicMock()
    verify_resp.session = MagicMock()
    verify_resp.session.access_token = "test-access-token"
    verify_resp.session.refresh_token = "test-refresh-token"
    mock.auth.verify_otp.return_value = verify_resp

    login_resp = MagicMock()
    login_resp.session = MagicMock()
    login_resp.session.access_token = "test-access-token"
    login_resp.session.refresh_token = "test-refresh-token"
    mock.auth.sign_in_with_password.return_value = login_resp

    refresh_resp = MagicMock()
    refresh_resp.session = MagicMock()
    refresh_resp.session.access_token = "new-access-token"
    refresh_resp.session.refresh_token = "new-refresh-token"
    mock.auth.refresh_session.return_value = refresh_resp

    mock.auth.sign_out.return_value = None
    mock.auth.admin.delete_user.return_value = None

    # storage stubs
    storage_mock = MagicMock()
    storage_mock.create_signed_upload_url.return_value = {"signedURL": "https://fake-storage/upload"}
    storage_mock.list.return_value = []
    storage_mock.remove.return_value = None
    storage_mock.download.return_value = b""
    mock.storage.from_.return_value = storage_mock

    return mock


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Patch Supabase client and Resend email for all tests."""
    mock_supabase = _make_mock_supabase()
    monkeypatch.setattr(supabase_module, "_client", mock_supabase)

    # Patch email functions
    monkeypatch.setattr(email_module, "send_checkin_email", lambda **kw: "msg-id")
    monkeypatch.setattr(email_module, "send_nomination_email", lambda **kw: "msg-id")
    monkeypatch.setattr(email_module, "send_delivery_email", lambda **kw: "msg-id")
    monkeypatch.setattr(email_module, "send_grace_period_reminder", lambda **kw: "msg-id")


async def _mock_db_session():
    session = AsyncMock()
    yield session


@pytest.fixture
async def client():
    from app.main import app
    from app.db.session import get_db_session
    app.dependency_overrides[get_db_session] = _mock_db_session
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
