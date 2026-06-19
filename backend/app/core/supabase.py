"""
Supabase client singleton — always uses the service role key for backend operations.
"""

from storage3 import SyncStorageClient
from supabase import create_client, Client
from app.config import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        cfg = get_settings()
        _client = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
    return _client


def get_supabase_admin() -> Client:
    """Fresh service-role client for Admin API calls (`auth.admin.*`).

    The shared get_supabase() singleton has its options.headers mutated by
    sign_in_with_password / sign_up / refresh_session / verify_otp — each
    emits a SIGNED_IN event that overwrites the service-role Authorization
    header with the calling user's JWT (same root cause documented on
    get_storage() below). `auth.admin.*` endpoints require the service-role
    key, so admin operations must use a client that is never used for those
    session calls. `create_client` performs no I/O, so building one per call
    is cheap and avoids sharing mutable auth state.
    """
    cfg = get_settings()
    return create_client(cfg.supabase_url, cfg.supabase_service_role_key)


def get_storage() -> SyncStorageClient:
    """Return a storage-only client using service role key.

    Supabase's SyncClient propagates SIGNED_IN auth events to the shared
    options.headers, replacing the service role Authorization with the user's
    JWT. Using a dedicated SyncStorageClient avoids that contamination.
    """
    cfg = get_settings()
    headers = {
        "apiKey": cfg.supabase_service_role_key,
        "Authorization": f"Bearer {cfg.supabase_service_role_key}",
    }
    return SyncStorageClient(f"{cfg.supabase_url}/storage/v1", headers, timeout=60)
