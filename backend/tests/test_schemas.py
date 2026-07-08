"""
Schema validation tests for all Pydantic models.
Verifies correct field types, required fields, and email validation.
"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.auth import SignupRequest, LoginRequest, VerifyEmailRequest, RefreshRequest, TokenResponse
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryUpdate, BeneficiaryResponse
from app.schemas.capsule import CapsuleCreate, CapsuleUpdate, CapsuleResponse
from app.schemas.checkin import CheckInSettingsUpdate, CheckInSettingsResponse
from app.schemas.user import UserResponse
from app.db.models.beneficiary import BeneficiaryStatus
from app.db.models.capsule import CapsuleStatus
from app.db.models.user import UserStatus


# ---------------------------------------------------------------------------
# SignupRequest
# ---------------------------------------------------------------------------

def test_signup_request_valid():
    obj = SignupRequest(
        email="user@example.com",
        password="StrongPassw0rd!",
        encrypted_cek="base64cek",
        cek_iv="base64iv",
        pbkdf2_salt="base64salt",
    )
    assert obj.email == "user@example.com"


def test_signup_request_weak_password_raises():
    with pytest.raises(ValidationError):
        SignupRequest(
            email="user@example.com",
            password="secret",  # <12 chars, no digit, no special char
            encrypted_cek="cek",
            cek_iv="iv",
            pbkdf2_salt="salt",
        )


def test_signup_request_missing_email_raises():
    with pytest.raises(ValidationError):
        SignupRequest(
            password="secret",
            encrypted_cek="cek",
            cek_iv="iv",
            pbkdf2_salt="salt",
        )


def test_signup_request_invalid_email_raises():
    with pytest.raises(ValidationError):
        SignupRequest(
            email="not-an-email",
            password="secret",
            encrypted_cek="cek",
            cek_iv="iv",
            pbkdf2_salt="salt",
        )


def test_signup_request_missing_password_raises():
    with pytest.raises(ValidationError):
        SignupRequest(
            email="user@example.com",
            encrypted_cek="cek",
            cek_iv="iv",
            pbkdf2_salt="salt",
        )


def test_signup_request_missing_encrypted_cek_raises():
    with pytest.raises(ValidationError):
        SignupRequest(
            email="user@example.com",
            password="secret",
            cek_iv="iv",
            pbkdf2_salt="salt",
        )


# ---------------------------------------------------------------------------
# LoginRequest
# ---------------------------------------------------------------------------

def test_login_request_valid():
    obj = LoginRequest(email="user@example.com", password="secret")
    assert obj.email == "user@example.com"


def test_login_request_missing_email_raises():
    with pytest.raises(ValidationError):
        LoginRequest(password="secret")


def test_login_request_invalid_email_raises():
    with pytest.raises(ValidationError):
        LoginRequest(email="bad-email", password="secret")


def test_login_request_missing_password_raises():
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com")


# ---------------------------------------------------------------------------
# VerifyEmailRequest
# ---------------------------------------------------------------------------

def test_verify_email_request_valid():
    obj = VerifyEmailRequest(email="user@example.com", otp="123456")
    assert obj.otp == "123456"


def test_verify_email_request_invalid_email_raises():
    with pytest.raises(ValidationError):
        VerifyEmailRequest(email="bad", otp="123456")


def test_verify_email_request_missing_otp_raises():
    with pytest.raises(ValidationError):
        VerifyEmailRequest(email="user@example.com")


# ---------------------------------------------------------------------------
# RefreshRequest
# ---------------------------------------------------------------------------

def test_refresh_request_valid():
    obj = RefreshRequest(refresh_token="some.jwt.token")
    assert obj.refresh_token == "some.jwt.token"


def test_refresh_request_missing_token_raises():
    with pytest.raises(ValidationError):
        RefreshRequest()


# ---------------------------------------------------------------------------
# TokenResponse
# ---------------------------------------------------------------------------

def test_token_response_valid():
    obj = TokenResponse(access_token="access", refresh_token="refresh")
    assert obj.token_type == "bearer"


def test_token_response_missing_access_token_raises():
    with pytest.raises(ValidationError):
        TokenResponse(refresh_token="refresh")


# ---------------------------------------------------------------------------
# BeneficiaryCreate
# ---------------------------------------------------------------------------

def test_beneficiary_create_valid():
    obj = BeneficiaryCreate(full_name="Jane Doe", email="jane@example.com")
    assert obj.is_emergency_contact is False
    assert obj.relationship is None
    # Notification defaults to on — silent add is opt-in.
    assert obj.notify_beneficiary is True


def test_beneficiary_create_silent():
    obj = BeneficiaryCreate(
        full_name="Jane Doe", email="jane@example.com", notify_beneficiary=False
    )
    assert obj.notify_beneficiary is False


def test_beneficiary_create_invalid_email_raises():
    with pytest.raises(ValidationError):
        BeneficiaryCreate(full_name="Jane", email="not-an-email")


def test_beneficiary_create_missing_email_raises():
    with pytest.raises(ValidationError):
        BeneficiaryCreate(full_name="Jane")


def test_beneficiary_create_missing_name_raises():
    with pytest.raises(ValidationError):
        BeneficiaryCreate(email="jane@example.com")


# ---------------------------------------------------------------------------
# BeneficiaryUpdate
# ---------------------------------------------------------------------------

def test_beneficiary_update_all_optional():
    obj = BeneficiaryUpdate()
    assert obj.full_name is None
    assert obj.email is None


def test_beneficiary_update_invalid_email_raises():
    with pytest.raises(ValidationError):
        BeneficiaryUpdate(email="bad-email")


def test_beneficiary_update_partial():
    obj = BeneficiaryUpdate(full_name="Jane Smith")
    assert obj.full_name == "Jane Smith"


# ---------------------------------------------------------------------------
# BeneficiaryResponse
# ---------------------------------------------------------------------------

def test_beneficiary_response_valid():
    obj = BeneficiaryResponse(
        id=uuid.uuid4(),
        full_name="Jane Doe",
        email="jane@example.com",
        relationship="spouse",
        is_emergency_contact=True,
        status=BeneficiaryStatus.active,
        created_at=datetime.now(timezone.utc),
    )
    assert obj.status == BeneficiaryStatus.active
    # invited_at is optional; None ⇒ silently-added beneficiary.
    assert obj.invited_at is None


def test_beneficiary_response_invited_at_roundtrip():
    now = datetime.now(timezone.utc)
    obj = BeneficiaryResponse(
        id=uuid.uuid4(),
        full_name="Jane Doe",
        email="jane@example.com",
        relationship=None,
        is_emergency_contact=False,
        status=BeneficiaryStatus.active,
        invited_at=now,
        created_at=now,
    )
    assert obj.invited_at == now


# ---------------------------------------------------------------------------
# CapsuleCreate
# ---------------------------------------------------------------------------

def test_capsule_create_valid():
    obj = CapsuleCreate(
        title="My Capsule",
        beneficiary_id=uuid.uuid4(),
        cipher_iv="base64iv",
    )
    assert obj.content_hash is None


def test_capsule_create_missing_title_raises():
    with pytest.raises(ValidationError):
        CapsuleCreate(beneficiary_id=uuid.uuid4(), cipher_iv="iv")


def test_capsule_create_invalid_beneficiary_uuid_raises():
    with pytest.raises(ValidationError):
        CapsuleCreate(title="Test", beneficiary_id="not-a-uuid", cipher_iv="iv")


def test_capsule_create_missing_cipher_iv_raises():
    with pytest.raises(ValidationError):
        CapsuleCreate(title="Test", beneficiary_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# CapsuleUpdate
# ---------------------------------------------------------------------------

def test_capsule_update_all_optional():
    obj = CapsuleUpdate()
    assert obj.title is None
    assert obj.delivery_order is None


def test_capsule_update_partial():
    obj = CapsuleUpdate(title="Updated", delivery_order=2)
    assert obj.delivery_order == 2


# ---------------------------------------------------------------------------
# CapsuleResponse
# ---------------------------------------------------------------------------

def test_capsule_response_valid():
    obj = CapsuleResponse(
        id=uuid.uuid4(),
        title="Test Capsule",
        status=CapsuleStatus.draft,
        delivery_order=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert obj.status == CapsuleStatus.draft
    # FR-22 zero-recipient flag defaults to True when unannotated
    assert obj.has_recipients is True


def test_capsule_create_negative_content_size_raises():
    with pytest.raises(ValidationError):
        CapsuleCreate(
            title="Test",
            beneficiary_id=uuid.uuid4(),
            cipher_iv="iv",
            content_size_bytes=-1,
        )


# ---------------------------------------------------------------------------
# CheckInSettingsUpdate
# ---------------------------------------------------------------------------

def test_checkin_settings_update_all_optional():
    obj = CheckInSettingsUpdate()
    assert obj.interval_days is None
    assert obj.grace_period_days is None


def test_checkin_settings_update_partial():
    obj = CheckInSettingsUpdate(interval_days=30)
    assert obj.interval_days == 30


# B4/FR-11: interval floor lowered from 7 to 1 day (permanent, all envs)
def test_checkin_settings_update_interval_below_min_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(interval_days=0)


def test_checkin_settings_update_interval_above_max_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(interval_days=366)


def test_checkin_settings_update_interval_bounds_accepted():
    assert CheckInSettingsUpdate(interval_days=1).interval_days == 1
    assert CheckInSettingsUpdate(interval_days=365).interval_days == 365


# B4/FR-12: grace period widened from Literal[3,7,14,30] to any int 1-30 —
# the frontend keeps offering the four presets, but the API no longer
# rejects other values.
def test_checkin_settings_update_grace_now_accepts_arbitrary_value():
    assert CheckInSettingsUpdate(grace_period_days=5).grace_period_days == 5


def test_checkin_settings_update_grace_below_min_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(grace_period_days=0)


def test_checkin_settings_update_grace_above_max_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(grace_period_days=31)


def test_checkin_settings_update_grace_valid_values_accepted():
    for value in (3, 7, 14, 30):
        assert CheckInSettingsUpdate(grace_period_days=value).grace_period_days == value


# Phase B: demo-mode minute overrides
def test_checkin_settings_update_minutes_default_none():
    obj = CheckInSettingsUpdate()
    assert obj.check_interval_minutes is None
    assert obj.grace_period_minutes is None
    assert obj.clear_minute_overrides is False


def test_checkin_settings_update_minutes_bounds_accepted():
    assert CheckInSettingsUpdate(check_interval_minutes=1).check_interval_minutes == 1
    assert CheckInSettingsUpdate(check_interval_minutes=1440).check_interval_minutes == 1440
    assert CheckInSettingsUpdate(grace_period_minutes=1).grace_period_minutes == 1
    assert CheckInSettingsUpdate(grace_period_minutes=1440).grace_period_minutes == 1440


def test_checkin_settings_update_interval_minutes_below_min_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(check_interval_minutes=0)


def test_checkin_settings_update_interval_minutes_above_max_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(check_interval_minutes=1441)


def test_checkin_settings_update_grace_minutes_below_min_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(grace_period_minutes=0)


def test_checkin_settings_update_grace_minutes_above_max_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(grace_period_minutes=1441)


# Phase B (extension): demo-mode override for the FR-23 emergency-contact
# confirmation window
def test_checkin_settings_update_emergency_confirm_minutes_default_none():
    assert CheckInSettingsUpdate().emergency_confirm_minutes is None


def test_checkin_settings_update_emergency_confirm_minutes_bounds_accepted():
    assert CheckInSettingsUpdate(emergency_confirm_minutes=1).emergency_confirm_minutes == 1
    assert CheckInSettingsUpdate(emergency_confirm_minutes=1440).emergency_confirm_minutes == 1440


def test_checkin_settings_update_emergency_confirm_minutes_below_min_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(emergency_confirm_minutes=0)


def test_checkin_settings_update_emergency_confirm_minutes_above_max_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsUpdate(emergency_confirm_minutes=1441)


# ---------------------------------------------------------------------------
# CheckInSettingsResponse
# ---------------------------------------------------------------------------

def test_checkin_settings_response_valid():
    obj = CheckInSettingsResponse(
        interval_days=30,
        grace_period_days=7,
        next_dispatch_at=None,
        last_confirmed_at=None,
        snooze_count=0,
        snooze_limit=2,
    )
    assert obj.snooze_limit == 2


def test_checkin_settings_response_missing_interval_raises():
    with pytest.raises(ValidationError):
        CheckInSettingsResponse(
            grace_period_days=7,
            next_dispatch_at=None,
            last_confirmed_at=None,
            snooze_count=0,
            snooze_limit=2,
        )


# ---------------------------------------------------------------------------
# UserResponse
# ---------------------------------------------------------------------------

def test_user_response_valid():
    obj = UserResponse(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="John Doe",
        email_verified=True,
        status=UserStatus.active,
        created_at=datetime.now(timezone.utc),
    )
    assert obj.email_verified is True


def test_user_response_invalid_email_raises():
    with pytest.raises(ValidationError):
        UserResponse(
            id=uuid.uuid4(),
            email="bad-email",
            full_name=None,
            email_verified=False,
            status=UserStatus.active,
            created_at=datetime.now(timezone.utc),
        )


def test_user_response_missing_id_raises():
    with pytest.raises(ValidationError):
        UserResponse(
            email="user@example.com",
            full_name=None,
            email_verified=False,
            status=UserStatus.active,
            created_at=datetime.now(timezone.utc),
        )
