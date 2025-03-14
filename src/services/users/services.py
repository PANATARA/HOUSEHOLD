from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core import constants
from core.hashing import Hasher
from core.services import BaseService
from db.dals.users import AsyncUserDAL, AsyncUserSettingsDAL
from db.models.user import User, UserSettings


@dataclass
class UserCreatorService(BaseService[User]):
    """Create and return a new Family"""

    username: str
    name: str
    surname: str
    password: str
    db_session: AsyncSession

    async def process(self) -> User:
        user = await self._create_user(
            {
                "username": self.username,
                "name": self.name,
                "surname": self.surname,
                "hashed_password": await self._get_hash_password(),
            }
        )
        settings_fields = constants.default_user_settings
        settings_fields["user_id"] = user.id
        await self._create_settings(settings_fields)
        return user

    async def _get_hash_password(self) -> str:
        return Hasher.get_password_hash(self.password)

    async def _create_user(self, fields: dict) -> User:
        user_dal = AsyncUserDAL(self.db_session)
        return await user_dal.create(fields)

    async def _create_settings(self, fields: dict) -> UserSettings:
        settings_dal = AsyncUserSettingsDAL(self.db_session)
        return await settings_dal.create(fields)
