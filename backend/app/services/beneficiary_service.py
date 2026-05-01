"""Business logic for beneficiary management."""

from sqlalchemy.ext.asyncio import AsyncSession


class BeneficiaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, full_name: str, email: str, relationship: str | None, is_emergency_contact: bool):
        """
        Insert beneficiary row and send nomination email.
        TODO: enforce unique (user_id, email) constraint gracefully.
        """
        raise NotImplementedError

    async def update(self, beneficiary_id: str, user_id: str, **kwargs):
        """
        Update beneficiary fields.
        If email changed, re-send nomination email to new address.
        TODO: implement.
        """
        raise NotImplementedError

    async def remove(self, beneficiary_id: str, user_id: str):
        """
        Set status = removed, record removed_at.
        Send removal notification to beneficiary.
        Unassign from linked capsules (do not delete capsules).
        TODO: implement.
        """
        raise NotImplementedError
