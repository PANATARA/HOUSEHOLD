from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import constants
from core.exceptions.users import UserAlreadyExistsError
from core.hashing import Hasher
from core.services import BaseService
from users.models import User, UserSettings
from users.repository import AsyncUserDAL, AsyncUserSettingsDAL
from users.schemas import UserCreateSchema


@dataclass
class UserCreatorService(BaseService[User]):
    """Create and return a new Family"""

    user_data: UserCreateSchema
    db_session: AsyncSession

    async def process(self) -> User:
        user = await self._create_user(
            {
                "username": self.user_data.username,
                "name": self.user_data.name,
                "surname": self.user_data.surname,
                "hashed_password": self._get_hash_password(),
            }
        )
        settings_fields = constants.default_user_settings
        settings_fields["user_id"] = user.id
        await self._create_settings(settings_fields)
        return user

    def _get_hash_password(self) -> str:
        return Hasher.get_password_hash(self.user_data.password)

    async def _create_user(self, fields: dict) -> User:
        user_dal = AsyncUserDAL(self.db_session)
        try:
            user = await user_dal.create(fields)
        except IntegrityError:
            raise UserAlreadyExistsError()
        else:
            return user

    async def _create_settings(self, fields: dict) -> UserSettings:
        settings_dal = AsyncUserSettingsDAL(self.db_session)
        return await settings_dal.create(fields)
