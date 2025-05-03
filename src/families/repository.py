from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_dals import BaseDals, GetOrRaiseMixin
from core.exceptions.families import FamilyNotFoundError
from families.models import Family
from families.schemas import FamilyDetailSchema
from users.models import User, UserFamilyPermissions


class AsyncFamilyDAL(BaseDals[Family], GetOrRaiseMixin[Family]):

    model = Family
    not_found_exception = FamilyNotFoundError

    async def get_family_admin(self, family_id: UUID) -> list[UUID] | None:
        pass

    async def user_is_family_admin(self, user_id: UUID, family_id: UUID) -> bool:
        query = select(
            exists().where(
                and_(Family.id == family_id, Family.family_admin_id == user_id)
            )
        )
        result = await self.db_session.execute(query)
        return bool(result.scalar())

    async def user_is_family_member(self, user_id: UUID, family_id: UUID) -> bool:
        query = select(
            exists().where(and_(User.id == user_id, User.family_id == family_id))
        )
        result = await self.db_session.execute(query)
        return bool(result.scalar())

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


@dataclass
class FamilyDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_with_members(
        self, family_id: UUID
    ) -> FamilyDetailSchema | None:
        """Returns a pydantic model of the family and its members"""
        result = await self.db_session.execute(
            select(
                func.json_build_object(
                    "id",
                    Family.id,
                    "name",
                    Family.name,
                    "icon",
                    Family.icon,
                ).label("family"),
                func.json_agg(
                    func.json_build_object(
                        "id",
                        User.id,
                        "username",
                        User.username,
                        "name",
                        User.name,
                        "surname",
                        User.surname,
                    )
                ).label("members"),
            )
            .join(User, Family.id == User.family_id)
            .where(Family.id == family_id)
            .group_by(Family.id)
        )

        rows = result.mappings().all()

        if rows is None:
            return None
        family = FamilyDetailSchema.model_validate(rows[0])

        return family
