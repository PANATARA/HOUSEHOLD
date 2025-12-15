from uuid import UUID

from sqlalchemy import select, update

from core.base_dals import BaseDals, BaseUserPkDals, DeleteDALMixin
from core.exceptions.users import UserNotFoundError
from users.models import User, UserFamilyPermissions, UserSettings


class UserRepository(BaseDals[User]):
    model = User
    not_found_exception = UserNotFoundError

    async def get_user_by_email(self, email: str) -> User:
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        if user:
            return user[0]
        else:
            raise self.not_found_exception

    async def increment_experience(self, user_id: UUID, value: int):
        await self.db_session.execute(
            update(User)
            .where(User.id == user_id)
            .values(experience=User.experience + value)
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

    async def get_users_should_confirm_chore_completion(
        self, family_id: UUID, excluded_user_ids: list[UUID]
    ) -> list[UUID] | None:
        query = (
            select(User.id)
            .join(UserFamilyPermissions, UserFamilyPermissions.user_id == User.id)
            .where(UserFamilyPermissions.should_confirm_chore_completion)
            .where(User.family_id == family_id)
            .where(User.id.notin_(excluded_user_ids))
        )
        query_result = await self.db_session.execute(query)
        users_ids = list(query_result.scalars().all())

        return users_ids if users_ids else None
