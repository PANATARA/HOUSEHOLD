from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import and_, exists, select

from core.base_dals import BaseDals
from db.models.family import Family
from db.models.user import User, UserFamilyPermissions


@dataclass
class AsyncFamilyDAL(BaseDals):

    class Meta:
        model = Family

    async def get_family_admin(self, family_id: UUID) -> list[UUID] | None:
        pass

    async def user_is_family_admin(self, user_id: UUID, family_id: UUID) -> bool:
        query = select(
            exists().where(
                and_(Family.id == family_id, Family.family_admin_id == user_id)
            )
        )
        result = await self.db_session.execute(query)
        return result.scalar()

    async def user_is_family_member(self, user_id: UUID, family_id: UUID) -> bool:
        query = select(
            exists().where(
                and_(User.id == user_id, User.family_id == family_id)
            )
        )
        result = await self.db_session.execute(query)
        return result.scalar()
        
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
        users_ids = query_result.scalars().all()

        return None if not users_ids else users_ids
