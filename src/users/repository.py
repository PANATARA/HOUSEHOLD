from datetime import date
from uuid import UUID

from sqlalchemy import or_, select, update

from core.base_dals import BaseDals, BaseUserPkDals, DeleteDALMixin
from core.exceptions.users import UserNotFoundError
from users.models import User, UserFamilyPermissions, UserSettings


class UserRepository(BaseDals[User]):
    model = User
    not_found_exception = UserNotFoundError

    async def get_by_username(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_by_username_or_email(self, identifier: str) -> User | None:
        query = select(User).where(
            or_(User.username == identifier, User.email == identifier)
        )
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_user_by_email(self, email: str) -> User:
        user = await self.get_by_username_or_email(email)
        if user:
            return user
        raise self.not_found_exception

    async def create_user_with_password(
        self,
        username: str,
        hashed_password: str,
        name: str | None = None,
        email: str | None = None,
        icon: str | None = None,
        icon_color: str | None = None,
        icon_bg: str | None = None,
    ) -> User:
        new_user = User(
            username=username,
            hashed_password=hashed_password,
            name=name or username,
            email=email,
            is_active=True,
            icon=icon or "material-symbols:person-rounded",
            icon_color=icon_color or "#ffffff",
            icon_bg=icon_bg or "linear-gradient(135deg, #F97316 0%, #FB7185 100%)",
        )
        self.db_session.add(new_user)
        await self.db_session.flush()
        await self.db_session.refresh(new_user)

        settings = UserSettings(
            user_id=new_user.id,
            app_theme="Dark",
            language="ru",
            date_of_birth=date(2001, 1, 1),
        )
        self.db_session.add(settings)
        await self.db_session.flush()

        return new_user

    async def get_by_google_sub_or_email(self, sub: str, email: str) -> User | None:
        conditions = [User.email == email]
        if sub:
            conditions.append(User.google_sub == sub)
        query = select(User).where(or_(*conditions))
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def upsert_google_user(
        self,
        sub: str,
        email: str,
        name: str | None = None,
    ) -> tuple[User, bool]:
        user = await self.get_by_google_sub_or_email(sub=sub, email=email)
        if user is not None:
            changed = False
            if sub and user.google_sub != sub:
                user.google_sub = sub
                changed = True
            if name and not user.name:
                user.name = name
                changed = True
            if changed:
                await self.db_session.flush()
                await self.db_session.refresh(user)
            return user, False

        # Create new user
        username_base = email.split("@")[0][:30]
        username = f"{username_base}_{sub[-6:] if sub else 'g'}"
        new_user = User(
            email=email,
            google_sub=sub,
            username=username,
            name=name,
            is_active=True,
        )
        self.db_session.add(new_user)
        await self.db_session.flush()
        await self.db_session.refresh(new_user)

        settings = UserSettings(
            user_id=new_user.id,
            app_theme="Dark",
            language="ru",
            date_of_birth=date(2001, 1, 1),
        )
        self.db_session.add(settings)
        await self.db_session.flush()

        return new_user, True

    async def increment_experience(self, user_id: UUID, value: int):
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(experience=User.experience + value)
        )
        await self.db_session.flush()

    async def decrement_experience(self, user_id: UUID, value: int):
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .where(User.experience >= value)
            .values(experience=User.experience - value)
        )
        await self.db_session.flush()

    async def increment_total_completed(self, user_id: UUID):
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(total_completed=User.total_completed + 1)
        )
        await self.db_session.flush()

    async def decrement_total_completed(self, user_id: UUID):
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .where(User.total_completed > 0)
            .values(total_completed=User.total_completed - 1)
        )
        await self.db_session.flush()


class UserSettingsRepository(BaseDals[UserSettings], BaseUserPkDals[UserSettings]):
    model = UserSettings


class UserPermissionsRepository(
    BaseDals[UserFamilyPermissions],
    BaseUserPkDals[UserFamilyPermissions],
    DeleteDALMixin,
):
    model = UserFamilyPermissions
