from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.users import UserAlreadyExistsError
from core.services import BaseService
from users.models import User, UserSettings
from users.repository import AsyncUserDAL, AsyncUserSettingsDAL


@dataclass
class UserCreatorService(BaseService[User]):
    email: str
    db_session: AsyncSession

    async def process(self) -> User:
        user = await self._create_user()
        await self._create_settings(user.id)
        return user

    async def _create_user(self) -> User:
        user_dal = AsyncUserDAL(self.db_session)
        username = self._get_username_by_email(self.email)
        new_user = User(username=username, email=self.email)
        try:
            user = await user_dal.create(object=new_user)
        except IntegrityError:
            raise UserAlreadyExistsError()
        else:
            return user

    async def _create_settings(self, user_id: UUID) -> UserSettings:
        settings = UserSettings(
            user_id=user_id,
            app_theme="Dark",
            language="ru",
            date_of_birth=date(2001, 1, 1),
        )
        settings_dal = AsyncUserSettingsDAL(self.db_session)
        return await settings_dal.create(settings)

    def _get_username_by_email(self, email: str) -> str:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        username = email.split("@")[0] + "_" + date_str
        return username
