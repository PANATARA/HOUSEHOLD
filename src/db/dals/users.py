from uuid import UUID

from core.base_dals import BaseDals, GetOrRaiseMixin
from core.exceptions.users import UserNotFoundError
from db.models.user import User, UserFamilyPermissions, UserSettings
from sqlalchemy import select


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


class AsyncUserSettingsDAL(BaseDals[UserSettings]):

    model = UserSettings

    async def get_settings_by_user_id(self, user_id):
        pass


class AsyncUserFamilyPermissionsDAL(BaseDals[UserFamilyPermissions]):

    model = UserFamilyPermissions


