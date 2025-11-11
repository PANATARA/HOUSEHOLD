from uuid import UUID

from sqlalchemy import select

from core.base_dals import BaseDals, BaseUserPkDals, DeleteDALMixin
from core.exceptions.users import UserNotFoundError
from users.models import User, UserFamilyPermissions, UserSettings
from users.schemas import UserResponseSchema


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

    async def get_users_by_ids(
        self,
        user_ids: list[UUID],
    ) -> list[UserResponseSchema]:
        if not user_ids:
            return []
        result = await self.db_session.execute(
            select(
                User.id, User.username, User.name, User.surname, User.avatar_version
            ).where(User.id.in_(user_ids))
        )
        rows = result.mappings().all()
        return [UserResponseSchema.model_validate(member) for member in rows]


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
