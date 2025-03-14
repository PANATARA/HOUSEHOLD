from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import UserSettings
from schemas.users import UserSettingsShow


@dataclass
class UserDataService:
    """Return User pydantic models"""

    db_session: AsyncSession

    async def get_user_settings(self, user_id: UUID) -> UserSettingsShow | None:
        """Returns a pydantic model of the user settings"""
        result = await self.db_session.execute(
            select(
                UserSettings.user_id.label("user_id"),
                UserSettings.app_theme.label("app_theme"),
            ).where(UserSettings.user_id == user_id)
        )

        rows = result.mappings().first()

        if not rows:
            return None

        settings = UserSettingsShow(
            user_id=rows["user_id"], app_theme=rows["app_theme"]
        )
        return settings
