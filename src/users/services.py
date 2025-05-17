from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.users import UserAlreadyExistsError
from core.services import BaseService
from users.models import User, UserSettings
from users.repository import AsyncUserDAL, AsyncUserSettingsDAL
from users.schemas import UserCreateSchema, UserSettingsCreateSchema


@dataclass
class UserCreatorService(BaseService[User]):
    """Create and return a new Family"""

    user_data: UserCreateSchema
    db_session: AsyncSession

    async def process(self) -> User:
        self.user_data.hash_password()
        user = await self._create_user()
        await self._create_settings(user.id)
        self._set_default_avatar()
        return user

    async def _create_user(self) -> User:
        user_dal = AsyncUserDAL(self.db_session)
        try:
            user = await user_dal.create(User(**self.user_data.model_dump()))
        except IntegrityError:
            raise UserAlreadyExistsError()
        else:
            return user

    async def _create_settings(self, user_id: UUID) -> UserSettings:
        data = UserSettingsCreateSchema(
            user_id=user_id,
            app_theme="Dark",
            language="ru",
            date_of_birth=date(2001, 1, 1),
        )
        settings_dal = AsyncUserSettingsDAL(self.db_session)
        return await settings_dal.create(data.model_dump())

    def _set_default_avatar(self) -> None:
        pass
