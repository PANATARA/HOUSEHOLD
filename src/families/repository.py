from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, func, select, update

from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.families import FamilyNotFoundError
from families.models import Event, Family
from families.schemas import EventResponseSchema
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
                User.id,
                User.username,
                User.name,
                User.icon,
                User.icon_color,
                User.icon_bg,
                User.experience,
            ).where(User.family_id == family_id)
        )
        rows = result.mappings().all()
        if rows is None:
            raise FamilyNotFoundError
        return [UserResponseSchema.model_validate(member) for member in rows]

    async def count_family_members(self, family_id: UUID) -> int:
        result = await self.db_session.execute(
            select(func.count(User.id)).where(User.family_id == family_id)
        )

        return result.scalar_one()

    async def increment_experience(self, family_id: UUID, value: int):
        await self.db_session.execute(
            update(Family)
            .where(Family.id == family_id)
            .values(experience=Family.experience + value)
        )
        await self.db_session.flush()

    async def increment_total_completed(self, family_id: UUID):
        await self.db_session.execute(
            update(Family)
            .where(Family.id == family_id)
            .values(total_completed=Family.total_completed + 1)
        )
        await self.db_session.flush()

    async def decrement_total_completed(self, family_id: UUID):
        await self.db_session.execute(
            update(Family)
            .where(Family.id == family_id)
            .where(Family.total_completed > 0)
            .values(total_completed=Family.total_completed - 1)
        )
        await self.db_session.flush()


class EventRepository(BaseDals[Event], DeleteDALMixin):
    model = Event
    not_found_exception = FamilyNotFoundError

    async def get_by_date_range(
        self,
        family_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[EventResponseSchema]:
        result = await self.db_session.execute(
            select(Event)
            .where(
                Event.family_id == family_id,
                Event.date >= date_from,
                Event.date < date_to,
            )
            .order_by(Event.date)
        )

        return [
            EventResponseSchema.model_validate(event)
            for event in result.scalars().all()
        ]

    async def get_upcoming(
        self,
        family_id: UUID,
        limit: int = 3,
    ) -> list[EventResponseSchema]:
        now = datetime.utcnow().date()
        result = await self.db_session.execute(
            select(Event)
            .where(
                Event.family_id == family_id,
                Event.date >= now,
            )
            .order_by(Event.date)
            .limit(limit)
        )
        return [
            EventResponseSchema.model_validate(event)
            for event in result.scalars().all()
        ]

    async def get_all_paginated(
        self,
        family_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[EventResponseSchema]:
        result = await self.db_session.execute(
            select(Event)
            .where(Event.family_id == family_id)
            .order_by(Event.date.desc(), Event.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            EventResponseSchema.model_validate(event)
            for event in result.scalars().all()
        ]

