from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select

from core.base_dals import BaseDals
from db.models.family import Family
from db.models.user import User, UserFamilyPermissions



@dataclass
class AsyncFamilyDAL(BaseDals):

    class Meta:
        model = Family
    
    async def get_family_admins(self, family_id: UUID) -> list[UUID] | None:
        query = select(User.id).where(
            (User.family_id == family_id) & (User.is_family_admin.is_(True))
        )
        query_result = await self.db_session.execute(query)
        rows = query_result.scalars().all()
        return None if not rows else rows

    async def get_users_should_confirm_chorelog(self, family_id: UUID, excluded_user_ids: list[UUID]) -> list[UUID] | None:
        query = (
            select(User.id)
                .join(UserFamilyPermissions, UserFamilyPermissions.user_id == User.id)
                .where(UserFamilyPermissions.should_confirm_chorelog)
                .where(User.family_id == family_id)
                .where(User.id.notin_(excluded_user_ids))
        )
        query_result = await self.db_session.execute(query)
        users_ids = query_result.scalars().all()
    
        return None if not users_ids else users_ids