from typing import Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.user import User, UserFamilyPermissions, UserSettings
from sqlalchemy import select

@dataclass
class AsyncUserDAL(BaseDals):
    db_session: AsyncSession

    class Meta:
        model = User

    async def get_user_by_username(self, username: str) -> Union[User, None]:
        query = select(User).where(User.username == username)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        if user is not None:
            return user[0]
    
    async def get_users_where_permission(self, family_id: UUID):
        pass



@dataclass
class AsyncUserSettingsDAL(BaseDals):
    db_session: AsyncSession

    async def get_settings_by_user_id(self, user_id):
        pass

    class Meta:
        model = UserSettings


@dataclass
class AsyncUserFamilyPermissionsDAL(BaseDals):
    db_session: AsyncSession

    class Meta:
        model = UserFamilyPermissions