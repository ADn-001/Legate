"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, field_validator


def _check_password_strength(v: str) -> str:
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
        raise ValueError("Password must contain at least one special character")
    return v


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)
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


class ResendOtpRequest(BaseModel):
    email: EmailStr


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


class SetPrimaryKeyRequest(BaseModel):
    """Re-wrap the primary CEK blob with a new password-derived key."""
    encrypted_cek: str    # base64
    cek_iv: str           # base64
    pbkdf2_salt: str      # base64


class SetRecoveryKeyRequest(BaseModel):
    """Set (or regenerate) the recovery-phrase-wrapped CEK blob."""
    recovery_encrypted_cek: str   # base64
    recovery_cek_iv: str          # base64
    recovery_salt: str            # base64
    recovery_phrase_hash: str     # hex SHA-256 of the normalized mnemonic


class RecoveryKeyResponse(BaseModel):
    recovery_encrypted_cek: str   # base64
    recovery_cek_iv: str          # base64
    recovery_salt: str            # base64


class ValidateRecoveryPhraseRequest(BaseModel):
    recovery_phrase_hash: str     # hex SHA-256 of the normalized mnemonic


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """T6.1/T6.3 (recovery-phrase path): complete a password reset.

    Authenticated via the Supabase recovery-link access token. The client
    has already unwrapped the CEK using the recovery phrase and re-wrapped
    it with the new password.
    """
    new_password: str
    encrypted_cek: str    # base64
    cek_iv: str           # base64
    pbkdf2_salt: str      # base64

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class ResetPasswordDataLossRequest(BaseModel):
    """T6.3 (legacy accounts with no recovery blob): reset the password and
    replace the CEK entirely. Existing capsule content becomes
    unrecoverable and is flagged accordingly."""
    new_password: str
    encrypted_cek: str    # base64, wraps a brand-new CEK
    cek_iv: str           # base64
    pbkdf2_salt: str      # base64

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """T6.4: logged-in password change, with the same CEK re-wrap treatment
    as the reset flow but using the current password to confirm identity."""
    current_password: str
    new_password: str
    encrypted_cek: str    # base64
    cek_iv: str           # base64
    pbkdf2_salt: str      # base64

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)
