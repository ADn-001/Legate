"""
Shared slowapi limiter instance (T7 / Phase 4).

Defined here to avoid circular imports between main.py and the API routers.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_storage_uri() -> str:
    try:
        from app.config import get_settings
        return get_settings().redis_url
    except Exception:
        return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_get_storage_uri(),
    # 100/minute for authenticated routes (T7/NFR-10). Auth endpoints apply
    # stricter per-route limits (5/minute). /health is exempt via middleware.
    default_limits=["100/minute"],
)
