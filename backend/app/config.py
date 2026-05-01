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

    # Storage
    supabase_storage_bucket_content: str = "capsule-content"
    supabase_storage_bucket_media: str = "media-attachments"
    supabase_storage_bucket_thumbnails: str = "thumbnails"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
