"""
Import all models here so Alembic can discover them for autogenerate.
"""
from app.db.models.user import User, UserSettings, EncryptionKey
from app.db.models.capsule import Capsule, CapsuleRecipient, MediaAttachment
from app.db.models.beneficiary import Beneficiary
from app.db.models.checkin import CheckInSchedule, CheckInEvent, ReleaseTrigger
from app.db.models.delivery import DeliveryEvent
from app.db.models.audit import AuditLog

__all__ = [
    "User", "UserSettings", "EncryptionKey",
    "Capsule", "CapsuleRecipient", "MediaAttachment",
    "Beneficiary",
    "CheckInSchedule", "CheckInEvent", "ReleaseTrigger",
    "DeliveryEvent",
    "AuditLog",
]
