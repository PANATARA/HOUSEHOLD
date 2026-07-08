from datetime import date
from uuid import UUID

from sqlalchemy import case, select, func
from sqlalchemy.orm import aliased

from chores.models import Chore
from planned_chores.models import ChoreSchedule, PlannedChore
from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.chores_completion import ChoreCompletionNotFoundError
from planned_chores.schemas import PlannedChoreResponseSchema
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
    not_found_exception = ChoreCompletionNotFoundError  # !Improve!
