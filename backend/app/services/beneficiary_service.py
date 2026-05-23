"""Business logic for beneficiary management."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.audit import write_audit
from app.core.email import send_nomination_email
from app.db.models.beneficiary import Beneficiary, BeneficiaryStatus
from app.db.models.capsule import CapsuleRecipient


class BeneficiaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        full_name: str,
        email: str,
        relationship: str | None,
        is_emergency_contact: bool,
        nominator_name: str,
    ) -> Beneficiary:
        # Enforce unique (user_id, email)
        existing = await self.db.execute(
            select(Beneficiary).where(
                and_(Beneficiary.user_id == user_id, Beneficiary.email == email)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Beneficiary with this email already exists")

        beneficiary = Beneficiary(
            user_id=user_id,
            full_name=full_name,
            email=email,
            relationship_type=relationship,
            is_emergency_contact=is_emergency_contact,
            status=BeneficiaryStatus.pending,
            invited_at=datetime.now(timezone.utc),
        )
        self.db.add(beneficiary)
        await self.db.flush()

        send_nomination_email(to=email, nominator_name=nominator_name)
        await write_audit(self.db, "beneficiary_added", user_id=user_id, resource_id=beneficiary.id)
        await self.db.commit()
        return beneficiary

    async def get(self, beneficiary_id: uuid.UUID, user_id: uuid.UUID) -> Beneficiary:
        result = await self.db.execute(
            select(Beneficiary).where(
                and_(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id)
            )
        )
        beneficiary = result.scalar_one_or_none()
        if not beneficiary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
        return beneficiary

    async def list_for_user(self, user_id: uuid.UUID) -> list[Beneficiary]:
        result = await self.db.execute(
            select(Beneficiary).where(Beneficiary.user_id == user_id)
        )
        return list(result.scalars().all())

    async def update(
        self,
        beneficiary_id: uuid.UUID,
        user_id: uuid.UUID,
        nominator_name: str,
        **kwargs,
    ) -> Beneficiary:
        beneficiary = await self.get(beneficiary_id, user_id)
        old_email = beneficiary.email

        field_map = {
            "full_name": "full_name",
            "email": "email",
            "relationship": "relationship_type",
            "is_emergency_contact": "is_emergency_contact",
        }
        for key, attr in field_map.items():
            if key in kwargs and kwargs[key] is not None:
                setattr(beneficiary, attr, kwargs[key])

        if "email" in kwargs and kwargs["email"] and kwargs["email"] != old_email:
            send_nomination_email(to=kwargs["email"], nominator_name=nominator_name)

        await write_audit(self.db, "beneficiary_updated", user_id=user_id, resource_id=beneficiary_id)
        await self.db.commit()
        return beneficiary

    async def remove(self, beneficiary_id: uuid.UUID, user_id: uuid.UUID) -> None:
        beneficiary = await self.get(beneficiary_id, user_id)
        beneficiary.status = BeneficiaryStatus.removed
        beneficiary.removed_at = datetime.now(timezone.utc)

        # Unassign from capsule_recipients
        result = await self.db.execute(
            select(CapsuleRecipient).where(CapsuleRecipient.beneficiary_id == beneficiary_id)
        )
        for recipient in result.scalars().all():
            await self.db.delete(recipient)

        await write_audit(self.db, "beneficiary_removed", user_id=user_id, resource_id=beneficiary_id)
        await self.db.commit()
