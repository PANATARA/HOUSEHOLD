from datetime import date
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased

from chores.models import Chore
from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.chores import ChoreScheduleNotFoundError
from core.exceptions.chores_completion import ChoreCompletionNotFoundError
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from planned_chores.schemas import (
    PlannedChoreResponseSchema,
    QuickPlannedChoreResponseSchema,
)
from users.models import User


class PlannedChoreRepository(BaseDals[PlannedChore], DeleteDALMixin):
    model = PlannedChore
    not_found_exception = ChoreCompletionNotFoundError  # !Improve!

    async def get_planned_chore_by_id(
        self, planned_chore_id: UUID
    ) -> PlannedChoreResponseSchema | None:

        UserCompleted = aliased(User)
        UserAssigned = aliased(User)

        query = (
            select(
                PlannedChore.id.label("id"),
                PlannedChore.schedule_id.label("schedule_id"),
                func.json_build_object(
                    "id",
                    Chore.id,
                    "name",
                    Chore.name,
                    "description",
                    Chore.description,
                    "icon",
                    Chore.icon,
                    "icon_color",
                    Chore.icon_color,
                    "icon_bg",
                    Chore.icon_bg,
                    "valuation",
                    Chore.valuation,
                    "default_chore_id",
                    Chore.default_chore_id,
                ).label("chore"),
                case(
                    (UserCompleted.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserCompleted.id,
                        "username",
                        UserCompleted.username,
                        "name",
                        UserCompleted.name,
                        "surname",
                        UserCompleted.surname,
                        "icon",
                        UserCompleted.icon,
                        "icon_color",
                        UserCompleted.icon_color,
                        "icon_bg",
                        UserCompleted.icon_bg,
                        "experience",
                        UserCompleted.experience,
                    ),
                ).label("completed_by"),
                case(
                    (UserAssigned.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserAssigned.id,
                        "username",
                        UserAssigned.username,
                        "name",
                        UserAssigned.name,
                        "surname",
                        UserAssigned.surname,
                        "icon",
                        UserAssigned.icon,
                        "icon_color",
                        UserAssigned.icon_color,
                        "icon_bg",
                        UserAssigned.icon_bg,
                        "experience",
                        UserAssigned.experience,
                    ),
                ).label("assigned_to"),
                PlannedChore.due_date.label("due_date"),
                PlannedChore.message.label("message"),
            )
            .join(Chore, PlannedChore.chore_id == Chore.id)
            .outerjoin(UserCompleted, PlannedChore.completed_by_id == UserCompleted.id)
            .outerjoin(UserAssigned, PlannedChore.assigned_to_id == UserAssigned.id)
            .where(
                PlannedChore.id == planned_chore_id,
                PlannedChore.is_active.is_(True),
            )
            .limit(1)
        )

        result = await self.db_session.execute(query)
        row = result.mappings().first()

        if not row:
            return None

        return PlannedChoreResponseSchema.model_validate(row)

    async def get_family_planned_chores(
        self,
        family_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[PlannedChoreResponseSchema]:
        conditions = [
            PlannedChore.family_id == family_id,
            PlannedChore.is_active.is_(True),
        ]

        if date_from is not None:
            conditions.append(PlannedChore.due_date >= date_from)

        if date_to is not None:
            conditions.append(PlannedChore.due_date <= date_to)

        UserCompleted = aliased(User)
        UserAssigned = aliased(User)

        query = (
            select(
                PlannedChore.id.label("id"),
                PlannedChore.schedule_id.label("schedule_id"),
                func.json_build_object(
                    "id",
                    Chore.id,
                    "name",
                    Chore.name,
                    "description",
                    Chore.description,
                    "icon",
                    Chore.icon,
                    "icon_color",
                    Chore.icon_color,
                    "icon_bg",
                    Chore.icon_bg,
                    "valuation",
                    Chore.valuation,
                    "default_chore_id",
                    Chore.default_chore_id,
                ).label("chore"),
                case(
                    (UserCompleted.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserCompleted.id,
                        "username",
                        UserCompleted.username,
                        "name",
                        UserCompleted.name,
                        "surname",
                        UserCompleted.surname,
                        "icon",
                        UserCompleted.icon,
                        "icon_color",
                        UserCompleted.icon_color,
                        "icon_bg",
                        UserCompleted.icon_bg,
                        "experience",
                        UserCompleted.experience,
                    ),
                ).label("completed_by"),
                case(
                    (UserAssigned.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserAssigned.id,
                        "username",
                        UserAssigned.username,
                        "name",
                        UserAssigned.name,
                        "surname",
                        UserAssigned.surname,
                        "icon",
                        UserAssigned.icon,
                        "icon_color",
                        UserAssigned.icon_color,
                        "icon_bg",
                        UserAssigned.icon_bg,
                        "experience",
                        UserAssigned.experience,
                    ),
                ).label("assigned_to"),
                PlannedChore.due_date.label("due_date"),
                PlannedChore.message.label("message"),
            )
            .join(Chore, PlannedChore.chore_id == Chore.id)
            .outerjoin(UserCompleted, PlannedChore.completed_by_id == UserCompleted.id)
            .outerjoin(UserAssigned, PlannedChore.assigned_to_id == UserAssigned.id)
            .where(*conditions)
            .order_by(PlannedChore.created_at.asc())
        )

        result = await self.db_session.execute(query)
        raw = result.mappings().all()

        return [PlannedChoreResponseSchema.model_validate(row) for row in raw]


class ChoreScheduleRepository(BaseDals[ChoreSchedule], DeleteDALMixin):
    model = ChoreSchedule
    not_found_exception = ChoreScheduleNotFoundError

    async def get_by_id(self, schedule_id: UUID) -> ChoreSchedule | None:
        query = select(self.model).where(self.model.id == schedule_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_chore_id(
        self, chore_id: UUID, active_only: bool = True
    ) -> ChoreSchedule | None:
        conditions = [self.model.chore_id == chore_id]
        if active_only:
            conditions.append(self.model.is_active.is_(True))
        query = (
            select(self.model)
            .where(*conditions)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_schedules_for_family(
        self, family_id: UUID
    ) -> list[ChoreSchedule]:
        query = (
            select(self.model)
            .where(
                self.model.family_id == family_id,
                self.model.is_active.is_(True),
            )
            .order_by(self.model.created_at.desc())
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_active(self) -> list[ChoreSchedule]:
        query = select(self.model).where(self.model.is_active.is_(True))
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    get_all_active_schedules = get_active


class QuickPlannedChoreRepository(BaseDals[QuickPlannedChore], DeleteDALMixin):
    model = QuickPlannedChore
    not_found_exception = ChoreCompletionNotFoundError  # !Improve!

    async def get_family_quick_chores(
        self,
        family_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[QuickPlannedChoreResponseSchema]:
        UserCompleted = aliased(User)
        UserAssigned = aliased(User)

        conditions = [
            QuickPlannedChore.family_id == family_id,
            QuickPlannedChore.is_active.is_(True),
        ]
        if date_from:
            conditions.append(QuickPlannedChore.due_date >= date_from)
        if date_to:
            conditions.append(QuickPlannedChore.due_date <= date_to)

        query = (
            select(
                QuickPlannedChore.id.label("id"),
                QuickPlannedChore.name.label("name"),
                QuickPlannedChore.description.label("description"),
                QuickPlannedChore.icon.label("icon"),
                QuickPlannedChore.icon_color.label("icon_color"),
                QuickPlannedChore.icon_bg.label("icon_bg"),
                QuickPlannedChore.valuation.label("valuation"),
                QuickPlannedChore.family_id.label("family_id"),
                QuickPlannedChore.is_active.label("is_active"),
                QuickPlannedChore.due_date.label("due_date"),
                QuickPlannedChore.message.label("message"),
                QuickPlannedChore.created_by.label("created_by"),
                case(
                    (UserCompleted.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserCompleted.id,
                        "name",
                        UserCompleted.name,
                        "surname",
                        UserCompleted.surname,
                        "icon",
                        UserCompleted.icon,
                        "icon_color",
                        UserCompleted.icon_color,
                        "icon_bg",
                        UserCompleted.icon_bg,
                        "experience",
                        UserCompleted.experience,
                    ),
                ).label("completed_by"),
                case(
                    (UserAssigned.id.is_(None), None),
                    else_=func.json_build_object(
                        "id",
                        UserAssigned.id,
                        "name",
                        UserAssigned.name,
                        "surname",
                        UserAssigned.surname,
                        "icon",
                        UserAssigned.icon,
                        "icon_color",
                        UserAssigned.icon_color,
                        "icon_bg",
                        UserAssigned.icon_bg,
                        "experience",
                        UserAssigned.experience,
                    ),
                ).label("assigned_to"),
            )
            .outerjoin(
                UserCompleted, QuickPlannedChore.completed_by_id == UserCompleted.id
            )
            .outerjoin(
                UserAssigned, QuickPlannedChore.assigned_to_id == UserAssigned.id
            )
            .where(*conditions)
            .order_by(QuickPlannedChore.created_at.asc())
        )

        result = await self.db_session.execute(query)
        return [
            QuickPlannedChoreResponseSchema.model_validate(row)
            for row in result.mappings().all()
        ]
