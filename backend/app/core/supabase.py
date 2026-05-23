"""
Supabase client singleton — always uses the service role key for backend operations.
"""

from supabase import create_client, Client
from app.config import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        cfg = get_settings()
        _client = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
    return _client
