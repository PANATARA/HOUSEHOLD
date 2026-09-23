from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.users import UserAlreadyExistsError
from core.services import BaseService
from users.models import User, UserSettings
from users.repository import UserRepository, UserSettingsRepository


@dataclass
class UserCreatorService(BaseService[User]):
    username: str
    db_session: AsyncSession
    password: str | None = None
    email: str | None = None
    name: str | None = None

    async def process(self) -> User:
        user = await self._create_user()
        await self._create_settings(user.id)
        return user

    async def _create_user(self) -> User:
        user_dal = UserRepository(self.db_session)
        from core.hashing import Hasher

        hashed_password = (
            Hasher.get_password_hash(self.password) if self.password else None
        )
        new_user = User(
            username=self.username,
            name=self.name or self.username,
            email=self.email,
            hashed_password=hashed_password,
        )
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
        settings_dal = UserSettingsRepository(self.db_session)
        return await settings_dal.create(settings)


def _generate_levels(total_levels: int = 100, max_exp: int = 10000) -> list[dict]:
    levels = []
    for level in range(1, total_levels + 1):
        # квадратичная кривая — начало пологое, конец крутой
        t = (level - 1) / (total_levels - 1)
        min_exp = round(max_exp * (t**2))
        levels.append({"level": level, "min_exp": min_exp})
    return levels


LEVELS = _generate_levels()


def get_level_info(experience: int) -> dict:
    current = LEVELS[0]
    next_level = None

    for i, lvl in enumerate(LEVELS):
        if experience >= lvl["min_exp"]:
            current = lvl
            next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None

    exp_to_next_total = next_level["min_exp"] if next_level else None

    if next_level:
        span = next_level["min_exp"] - current["min_exp"]
        exp_in_level = experience - current["min_exp"]
        progress = round(exp_in_level / span * 100)
    else:
        progress = 100

    return {
        "level": current["level"],
        "exp_to_next_total": exp_to_next_total,
        "progress_percent": progress,
        "is_max_level": next_level is None,
    }
