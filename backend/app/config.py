"""
Application configuration loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Substrings that indicate a placeholder / known-weak secret.
_WEAK_FRAGMENTS = ("fake", "changeme", "secret", "example", "replace", "placeholder")

# Minimum length for secret values.
_SECRET_MIN_LEN = 32


def _validate_secret(field_name: str, value: str) -> str:
    """Raise ValueError if *value* is obviously weak (too short or contains a
    known placeholder fragment).  Callers embed this in model_validator so that
    pydantic raises a clear startup error rather than silently running with a
    derivable key.

    Generate compliant values with::

        openssl rand -base64 48
    """
    if len(value) < _SECRET_MIN_LEN:
        raise ValueError(
            f"{field_name} is too short ({len(value)} chars, minimum {_SECRET_MIN_LEN}). "
            "Generate with: openssl rand -base64 48"
        )
    lower = value.lower()
    for frag in _WEAK_FRAGMENTS:
        if frag in lower:
            raise ValueError(
                f"{field_name} contains a known-weak placeholder fragment ({frag!r}). "
                "Generate with: openssl rand -base64 48"
            )
    return value


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
    # These fields have NO default — startup fails loudly if they are unset or weak.
    # Generate compliant values with: openssl rand -base64 48
    supabase_jwt_secret: str
    delivery_secret: str
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


    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Reject obviously-weak values for all secret fields at startup."""
        _validate_secret("SUPABASE_JWT_SECRET", self.supabase_jwt_secret)
        _validate_secret("DELIVERY_SECRET", self.delivery_secret)
        _validate_secret("SECRET_KEY", self.secret_key)
        return self

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
