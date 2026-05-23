"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v
    encrypted_cek: str           # base64-encoded
    cek_iv: str                  # base64-encoded
    pbkdf2_salt: str             # base64-encoded
    delivery_encrypted_cek: str | None = None  # base64-encoded
    delivery_cek_iv: str | None = None         # base64-encoded


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class EncryptionKeyResponse(BaseModel):
    encrypted_cek: str      # base64
    cek_iv: str             # base64
    pbkdf2_salt: str        # base64
    pbkdf2_iterations: int


class DeliveryWrappingKeyResponse(BaseModel):
    wrapping_key: str       # HMAC-SHA256 hex
