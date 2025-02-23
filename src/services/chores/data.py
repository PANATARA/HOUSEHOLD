from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from db.dals.chores import AsyncChoreDAL
from db.dals.families import AsyncFamilyDAL
from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.models.user import User
from schemas.chores import ChoreShow, ChoresResponse
from schemas.chores_logs import ChoreConfirmation, ChoreCompletionShow
from schemas.families import FamilyFullShow
from schemas.users import UserResponse


@dataclass
class ChoreDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_chores(self, family_id: UUID):
        """Returns a pydantic model of the chores"""
        chore_dal = AsyncChoreDAL(self.db_session)
        rows = await chore_dal.get_family_chores(family_id)

        if not rows:
            return None

        chores = [
            ChoreShow(
                id=row["chore_id"],
                name=row["chore_name"],
                description=row["chore_description"],
                icon=row["chore_icon"],
                valuation=row["chore_valuation"],
            )
            for row in rows
        ]
        
        return ChoresResponse(chores=chores)



@dataclass
class ChoreConfirmationDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_user_chore_confirmations(self, user_id) -> list[ChoreConfirmation]:
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
                cl.message.label("chore_completion_message"),
                cl.created_at.label("chore_completion_completed_at"),
                cl.status.label("chore_completion_status"),
                u.id.label("completed_by_id"),
                u.username.label("completed_by_username"),
                u.name.label("completed_by_name"),
                u.surname.label("completed_by_surname"),
                c.id.label("chore_id"),
                c.name.label("chore_name"),
                c.description.label("chore_description"),
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
            ChoreConfirmation(
                id=data["chore_confirmation_id"],
                status=data["chore_confirmation_status"],
                chore_completion=ChoreCompletionShow(
                    id=data["chore_completion_id"],
                    completed_at=data["chore_completion_completed_at"],
                    message=data["chore_completion_message"],
                    status=data["chore_completion_status"],
                    completed_by=UserResponse(
                        id=data["completed_by_id"],
                        username=data["completed_by_username"],
                        name=data["completed_by_name"],
                        surname=data["completed_by_surname"]
                    ),
                    chore=ChoreShow(
                        id=data["chore_id"],
                        name=data["chore_name"],
                        description=data["chore_description"],
                        icon=data["chore_icon"],
                        valuation=data["chore_valuation"]
                    )
                )
            )
            for data in raw_data
        ]

        return confirmations 
