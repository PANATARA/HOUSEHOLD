from collections import defaultdict
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.models.user import User
from schemas.chores.chores import NewChoreDetail, NewChoreSummary
from schemas.chores.chores_completions import NewChoreCompletion, NewChoreCompletionSummary
from schemas.chores.compositions import NewChoreConfirmationDetail, NewChoreDetailMax
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
    
    async def get_family_chore_with_chore_completions(self, chore_id: UUID, limit: int, offset: int) -> list[NewChoreDetailMax]:
        query = (
            select(
                Chore.id.label("chore_id"),
                Chore.name.label("chore_name"),
                Chore.description.label("chore_description"),
                Chore.icon.label("chore_icon"),
                Chore.valuation.label("chore_valuation"),
                Chore.created_at.label("chore_created_at"),
                ChoreCompletion.id.label("chore_completion_id"),
                User.id.label("chore_completion_user_id"),
                User.username.label("chore_completion_user_username"),
                User.name.label("chore_completion_user_name"),
                User.surname.label("chore_completion_user_surname"),
                ChoreCompletion.created_at.label("chore_completion_completed_at"),
                ChoreCompletion.status.label("chore_completion_status"),
                ChoreCompletion.message.label("chore_completion_message")
            )
            .select_from(Chore)
            .join(ChoreCompletion, ChoreCompletion.chore_id == Chore.id, isouter=True)
            .join(User, User.id == ChoreCompletion.completed_by_id, isouter=True)
            .where(Chore.id == chore_id)
            .limit(limit)
            .offset(offset) 
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        chore_dict = defaultdict(lambda: {"chore": {}, "chores_completion": []})
        for row in raw_data:
            chore_id = row["chore_id"]
            chore_dict[chore_id]["chore"] = {
                "id": row["chore_id"],
                "name": row["chore_name"],
                "description": row["chore_description"],
                "icon": row["chore_icon"],
                "valuation": row["chore_valuation"],
                "created_at": row["chore_created_at"]
            }
            chore_dict[chore_id]["chores_completion"].append(
                {
                    "id": row["chore_completion_id"],
                    "completed_by": {
                        "id": row["chore_completion_user_id"],
                        "username": row["chore_completion_user_username"],
                        "name": row["chore_completion_user_name"],
                        "surname": row["chore_completion_user_surname"]
                    },
                    "completed_at": row["chore_completion_completed_at"],
                    "status": row["chore_completion_status"],
                    "message": row["chore_completion_message"]
                    } if row["chore_completion_id"] else None
            )

        grouped_data = list(chore_dict.values())
        chores_details = []

        for item in grouped_data:
            chores_details.append(
                NewChoreDetailMax.model_validate(item)
            )
        return chores_details


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
