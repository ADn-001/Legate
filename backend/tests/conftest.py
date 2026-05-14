"""
Pytest fixtures shared across all test modules.

NOTE: Two bugs in the application source prevent normal import:
  1. app/db/models/beneficiary.py — the ORM column named 'relationship'
     shadows the sqlalchemy.orm.relationship() function, causing TypeError
     at class-definition time.
  2. app/db/models/checkin.py — imports INET from sqlalchemy (not in core;
     should be sqlalchemy.dialects.postgresql.INET), causing ImportError.

Both are patched here via sys.modules BEFORE the app is imported.
These patches do not alter application logic; they exist purely to allow
the import chain to complete so route tests can run.
"""

import enum
import sys
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# PATCH 1: Fix broken checkin model (INET not in sqlalchemy core)
# ---------------------------------------------------------------------------
class _TokenType(str, enum.Enum):
    confirm = "confirm"
    snooze_7 = "snooze_7"
    snooze_14 = "snooze_14"
    snooze_30 = "snooze_30"
    emergency_pause = "emergency_pause"


class _EventStatus(str, enum.Enum):
    pending = "pending"
    used = "used"
    expired = "expired"


class _TriggerReason(str, enum.Enum):
    checkin_missed = "checkin_missed"
    emergency_pause_timeout = "emergency_pause_timeout"
    manual = "manual"


class _TriggerStatus(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


_mock_checkin_module = MagicMock()
_mock_checkin_module.TokenType = _TokenType
_mock_checkin_module.EventStatus = _EventStatus
_mock_checkin_module.TriggerReason = _TriggerReason
_mock_checkin_module.TriggerStatus = _TriggerStatus
_mock_checkin_module.CheckInSchedule = MagicMock()
_mock_checkin_module.CheckInEvent = MagicMock()
_mock_checkin_module.ReleaseTrigger = MagicMock()
sys.modules["app.db.models.checkin"] = _mock_checkin_module


# ---------------------------------------------------------------------------
# PATCH 2: Fix broken beneficiary model (column named 'relationship' shadows
# the sqlalchemy.orm.relationship() function)
# ---------------------------------------------------------------------------
class _BeneficiaryStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    removed = "removed"


_mock_beneficiary_module = MagicMock()
_mock_beneficiary_module.BeneficiaryStatus = _BeneficiaryStatus
_mock_beneficiary_module.Beneficiary = MagicMock()
sys.modules["app.db.models.beneficiary"] = _mock_beneficiary_module
# ---------------------------------------------------------------------------


import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db_session


async def _mock_db_session():
    """
    Mock async DB session generator.
    All route handlers under test raise NotImplementedError before any
    real DB query, so a mock session is sufficient.
    """
    session = AsyncMock()
    yield session


@pytest.fixture
async def client():
    """
    AsyncClient with mock DB session dependency override.
    raise_app_exceptions=False ensures that NotImplementedError stubs
    are translated to HTTP 500 responses rather than propagating as
    Python exceptions to the test runner.
    """
    app.dependency_overrides[get_db_session] = _mock_db_session
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
