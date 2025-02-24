from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.models.user import User
from schemas.chores import NewChoreSummary
from schemas.chores_completions import (
    NewChoreConfirmationDetail,
    NewChoreCompletionSummary,
)
from schemas.users import UserResponse


@dataclass
class ChoreDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_chores(self, family_id: UUID) -> list[NewChoreSummary]:
        """Returns a pydantic model of the chores"""
        query = select(
            Chore.id,
            Chore.name,
            Chore.icon,
            Chore.valuation,
        ).where(Chore.family_id == family_id)

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        if not raw_data:
            return None

        return [NewChoreSummary.model_validate(item) for item in raw_data]


@dataclass
class ChoreConfirmationDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_user_chore_confirmations(
        self, user_id: UUID
    ) -> list[NewChoreConfirmationDetail]:
        clc = aliased(ChoreConfirmation)
        cl = aliased(ChoreCompletion)
        c = aliased(Chore)
        u = aliased(User)

        query = (
            select(
                clc.id.label("chore_confirmation_id"),
                clc.status.label("chore_confirmation_status"),
                clc.created_at.label("chore_confirmation_created_at"),
                cl.id.label("chore_completion_id"),
                cl.created_at.label("chore_completion_completed_at"),
                cl.status.label("chore_completion_status"),
                u.id.label("completed_by_id"),
                u.username.label("completed_by_username"),
                u.name.label("completed_by_name"),
                u.surname.label("completed_by_surname"),
                c.id.label("chore_id"),
                c.name.label("chore_name"),
                c.icon.label("chore_icon"),
                c.valuation.label("chore_valuation"),
            )
            .join(cl, clc.chore_completion_id == cl.id)
            .join(c, cl.chore_id == c.id)
            .join(u, cl.completed_by_id == u.id)
            .where(clc.user_id == user_id)
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        confirmations = [
            NewChoreConfirmationDetail(
                id=data["chore_confirmation_id"],
                status=data["chore_confirmation_status"],
                chore_completion=NewChoreCompletionSummary(
                    id=data["chore_completion_id"],
                    completed_at=data["chore_completion_completed_at"],
                    status=data["chore_completion_status"],
                    completed_by=UserResponse(
                        id=data["completed_by_id"],
                        username=data["completed_by_username"],
                        name=data["completed_by_name"],
                        surname=data["completed_by_surname"],
                    ),
                    chore=NewChoreSummary(
                        id=data["chore_id"],
                        name=data["chore_name"],
                        icon=data["chore_icon"],
                        valuation=data["chore_valuation"],
                    ),
                ),
            )
            for data in raw_data
        ]

        return confirmations
