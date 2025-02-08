from uuid import UUID
from dataclasses import dataclass
from sqlalchemy import select

from core.base_dals import BaseDals
from db.models.family import Family
from db.models.user import User



@dataclass
class AsyncFamilyDAL(BaseDals):

    class Meta:
        model = Family

    async def get_family_with_users(self, family_id: UUID) -> list[dict] | None:
        result = await self.db_session.execute(
            select(
                Family.id.label("family_id"),
                Family.name.label("family_name"),
                User.id.label("user_id"),
                User.username.label("user_username"),
                User.name.label("user_name"),
                User.surname.label("user_surname"),
            )
            .join(User, Family.id == User.family_id)
            .where(Family.id == family_id)
        )

        rows = result.mappings().all()

        if not rows:
            return None
        return rows
    
    async def get_family_admins(self, family_id: UUID) -> list[UUID] | None:
        query = select(User.id).where(
            (User.family_id == family_id) & (User.is_family_admin.is_(True))
        )
        query_result = await self.db_session.execute(query)
        rows = query_result.scalars().all()
        return None if not rows else rows
