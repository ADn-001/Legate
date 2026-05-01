"""Business logic for check-in token validation and schedule management."""

from sqlalchemy.ext.asyncio import AsyncSession


class CheckInService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def confirm(self, token: str, ip: str, user_agent: str):
        """
        Validate confirm token, mark used, reset schedule.
        TODO: implement token lookup + schedule update.
        """
        raise NotImplementedError

    async def snooze(self, token: str, days: int):
        """
        Validate snooze token, enforce snooze_limit, extend next_dispatch_at.
        TODO: implement.
        """
        raise NotImplementedError

    async def emergency_pause(self, token: str):
        """
        Validate emergency pause token, enforce pause_count < 2.
        Extend grace period by 7 days.
        TODO: implement.
        """
        raise NotImplementedError
