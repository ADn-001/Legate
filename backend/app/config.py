"""
Application configuration loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "Legate"
    debug: bool = False
    secret_key: str
    environment: str = "development"
    # ASGI root path when served behind a prefix-stripping proxy (e.g. nginx /api/)
    root_path: str = ""
    # Comma-separated list of allowed CORS origins; empty -> dev localhost defaults
    cors_origins: str = ""

    # Database
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Email (Resend)
    resend_api_key: str
    email_from: str = "noreply@legate.app"

    # PBKDF2
    pbkdf2_iterations: int = 100000

    # Supabase JWT + delivery
    supabase_jwt_secret: str = "fake-jwt-secret"
    delivery_secret: str = "fake-delivery-secret"
    base_url: str = "http://localhost:8000"
    # T6: base URL of the frontend SPA, used as the Supabase password-reset
    # magic-link redirect target (-> {frontend_url}/auth/reset-password).
    frontend_url: str = "http://localhost:5173"

    # Storage
    supabase_storage_bucket_content: str = "capsule-content"
    supabase_storage_bucket_media: str = "media-attachments"
    supabase_storage_bucket_thumbnails: str = "thumbnails"
    # Per-user storage quota for the FR-36 progress bar (default 1 GiB)
    storage_quota_bytes: int = 1073741824

    # Internal operational alerts (B6: permanent delivery failure).
    # Empty string disables alert emails (audit log row is always written).
    alert_email: str = ""


    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed CORS origins. Falls back to dev localhost ports when unset."""
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if origins:
            return origins
        return [f"http://localhost:{p}" for p in range(5173, 5180)] + [
            f"http://127.0.0.1:{p}" for p in range(5173, 5180)
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
