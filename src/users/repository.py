from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_dals import BaseDals, BaseUserPkDals, DeleteDALMixin, GetOrRaiseMixin
from core.exceptions.users import UserNotFoundError
from users.models import User, UserFamilyPermissions, UserSettings
from users.schemas import UserSettingsResponseSchema


class AsyncUserDAL(BaseDals[User], GetOrRaiseMixin[User]):

    model = User
    not_found_exception = UserNotFoundError

    async def get_user_by_username(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        return user[0] if user is not None else None

    async def get_users_where_permission(self, family_id: UUID):
        pass


class AsyncUserSettingsDAL(BaseUserPkDals[UserSettings]):

    model = UserSettings


class AsyncUserFamilyPermissionsDAL(
    BaseUserPkDals[UserFamilyPermissions], DeleteDALMixin
):

    model = UserFamilyPermissions


@dataclass
class UserDataService:
    """Return User pydantic models"""

    db_session: AsyncSession

    async def get_user_settings(
        self, user_id: UUID
    ) -> UserSettingsResponseSchema | None:
        """Returns a pydantic model of the user settings"""
        result = await self.db_session.execute(
            select(
                UserSettings.user_id.label("user_id"),
                UserSettings.app_theme,
                UserSettings.language,
                UserSettings.date_of_birth,
            ).where(UserSettings.user_id == user_id)
        )

        rows = result.mappings().first()

        if not rows:
            return None

        settings = UserSettingsResponseSchema.model_validate(rows)
        return settings
