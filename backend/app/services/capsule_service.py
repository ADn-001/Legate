"""Business logic for capsule CRUD operations."""

from sqlalchemy.ext.asyncio import AsyncSession


class CapsuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: str) -> list:
        """Return all non-deleted capsules for a user. TODO: implement."""
        raise NotImplementedError

    async def create(self, user_id: str, title: str, beneficiary_id: str, cipher_iv: str, content_hash: str | None):
        """
        Insert capsule row and capsule_recipient row.
        Return presigned Supabase Storage upload URL.
        TODO: implement.
        """
        raise NotImplementedError

    async def get_by_id(self, capsule_id: str, user_id: str):
        """Fetch capsule, enforce ownership. TODO: implement."""
        raise NotImplementedError

    async def update(self, capsule_id: str, user_id: str, **kwargs):
        """Update mutable capsule fields. TODO: implement."""
        raise NotImplementedError

    async def delete(self, capsule_id: str, user_id: str):
        """
        Set status = pending_deletion.
        Enqueue purge_capsule task for 24h later.
        TODO: implement.
        """
        raise NotImplementedError
