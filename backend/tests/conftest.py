"""
Pytest fixtures shared across all test modules.

Phase 2 (T-test): the AsyncMock session fixtures are gone. The `client`
fixture now serves requests against the REAL test database — the same
engine/configuration as tests/e2e/conftest.py (NullPool to avoid asyncpg
event-loop issues). External services are not mocked: the unit tests in
tests/test_*.py exercise request-validation and auth-rejection paths that are
answered before any Supabase/Resend call is made, and anything deeper lives
in tests/e2e/ against live services.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.config import get_settings

_cfg = get_settings()
_engine = create_async_engine(
    _cfg.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=NullPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def _real_db_session():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def db_session():
    """Direct real-DB session for assertions in unit tests."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    from app.main import app
    from app.db.session import get_db_session

    previous = app.dependency_overrides.get(get_db_session)
    app.dependency_overrides[get_db_session] = _real_db_session
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Restore rather than clear() so a session-scoped e2e override (if tests
    # run in the same pytest session) is not destroyed.
    if previous is not None:
        app.dependency_overrides[get_db_session] = previous
    else:
        app.dependency_overrides.pop(get_db_session, None)
