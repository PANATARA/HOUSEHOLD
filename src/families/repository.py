from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.click_house_connection import get_click_house_client
from analytics.repository import ChoreAnalyticRepository
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

    async def get_family_with_members(self, family_id: UUID) -> FamilyDetailSchema | None:
        """Returns a pydantic model of the family and its members"""
        result = await self.db_session.execute(
            select(
                Family.id,
                Family.name,
                Family.icon,
                func.json_agg(
                    func.json_build_object(
                        "id",User.id,
                        "username",User.username,
                        "name",User.name,
                        "surname",User.surname,
                    )
                ).label("members")
                
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

    async def get_family_with_members_sorted_by_completions(
        self, family_id: UUID, interval_start: date, interval_end: date
    ) -> FamilyDetailSchema | None:

        family = await self.get_family_with_members(family_id)
        if not family:
            return None

        async_click_house_client = await get_click_house_client()
        analytic_repo = ChoreAnalyticRepository(async_click_house_client)
        users_stats = await analytic_repo.get_family_members_by_chores_completions(
            family_id, interval_start, interval_end
        )
        stats_map = {row[0]: row[1] for row in users_stats}

        family.members.sort(
            key=lambda member: stats_map.get(member.id, 0),
            reverse=True,
        )

        return family
