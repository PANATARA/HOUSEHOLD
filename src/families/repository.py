from uuid import UUID

from sqlalchemy import and_, exists, select, update

from core.base_dals import BaseDals
from core.exceptions.families import FamilyNotFoundError
from families.models import Family
from users.models import User
from users.schemas import UserResponseSchema


class FamilyRepository(BaseDals[Family]):
    model = Family
    not_found_exception = FamilyNotFoundError

    async def user_is_family_admin(self, user_id: UUID, family_id: UUID) -> bool:
        query = select(
            exists().where(
                and_(Family.id == family_id, Family.family_admin_id == user_id)
            )
        )
        result = await self.db_session.execute(query)
        return bool(result.scalar())

    async def get_family_members(self, family_id: UUID) -> list[UserResponseSchema]:
        """Returns a pydantic model of the family and its members"""
        result = await self.db_session.execute(
            select(
                User.id, User.username, User.name, User.surname, User.avatar_version
            ).where(User.family_id == family_id)
        )
        rows = result.mappings().all()
        if rows is None:
            raise FamilyNotFoundError
        return [UserResponseSchema.model_validate(member) for member in rows]

    async def increment_experience(self, family_id: UUID, value: int):
        await self.db_session.execute(
            update(Family)
            .where(Family.id == family_id)
            .values(experience=Family.experience + value)
        )
        await self.db_session.flush()
