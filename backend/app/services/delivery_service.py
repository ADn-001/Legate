"""
Delivery pipeline logic.
Called by Celery delivery worker when a release trigger fires.
This service handles decryption (in-memory only), email rendering, and send.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class DeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_delivery(self, trigger_id: str):
        """
        Full delivery pipeline for a given release trigger:
        TODO: implement delivery flow.
        """
        raise NotImplementedError
