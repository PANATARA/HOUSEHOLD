from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from sqlalchemy import case


from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.models.user import User
from schemas.chores.chores import NewChoreSummary
from schemas.chores.chores_completions import NewChoreCompletionSummary
from schemas.chores.chores_confirmations import NewChoreConfirmationSummary
from schemas.chores.compositions import NewChoreCompletionDetail
from schemas.users import UserResponse


@dataclass
class ChoreCompletionDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_chore_completion(
        self, family_id: UUID, offset: int, limit: int
    ) -> list[NewChoreCompletionSummary]:
        """Returns a pydantic model of the chores logs"""
        cl = aliased(ChoreCompletion)
        c = aliased(Chore)
        u = aliased(User)

        query = (
            select(
                cl.id.label("chore_completion_id"),
                c.id.label("chore_id"),
                c.name.label("chore_name"),
                c.icon.label("chore_icon"),
                c.valuation.label("chore_valuation"),
                u.id.label("completed_by_id"),
                u.username.label("completed_by_username"),
                u.name.label("completed_by_name"),
                u.surname.label("completed_by_surname"),
                cl.created_at.label("chore_completion_completed_at"),
                cl.status.label("chore_completion_status"),
            )
            .join(u, cl.completed_by_id == u.id)
            .join(c, cl.chore_id == c.id)
            .where(c.family_id == family_id)
            .order_by(cl.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        chores_completions = [
            NewChoreCompletionSummary(
                id=data["chore_completion_id"],
                chore=NewChoreSummary(
                    id=data["chore_id"],
                    name=data["chore_name"],
                    icon=data["chore_icon"],
                    valuation=data["chore_valuation"],
                ),
                completed_by=UserResponse(
                    id=data["completed_by_id"],
                    username=data["completed_by_username"],
                    name=data["completed_by_name"],
                    surname=data["completed_by_surname"],
                ),
                completed_at=data["chore_completion_completed_at"],
                status=data["chore_completion_status"],
            )
            for data in raw_data
        ]
        return chores_completions

    async def get_family_chore_completion_detail(
        self, chore_completion_id: UUID
    ) -> NewChoreCompletionDetail | None:
        confirm_user = aliased(User)

        query = (
            select(
                ChoreCompletion.id.label("id"),
                func.json_build_object(
                    "id", Chore.id,
                    "name", Chore.name,
                    "icon", Chore.icon,
                    "valuation", Chore.valuation,
                ).label("chore"),
                func.json_build_object(
                    "id", User.id.label("id"),
                    "username", User.username,
                    "name", User.name,
                    "surname", User.surname
                ).label("completed_by"),
                ChoreCompletion.created_at.label("completed_at"),
                ChoreCompletion.message.label("message"),
                ChoreCompletion.status.label("status"),
                func.json_agg(
                    case(
                        (
                            ChoreConfirmation.id.isnot(None), 
                            func.json_build_object(
                                "id", ChoreConfirmation.id,
                                "user", func.json_build_object(
                                    "id", confirm_user.id,
                                    "username", confirm_user.username,
                                    "name", confirm_user.name,
                                    "surname", confirm_user.surname,
                                ),
                                "status", ChoreConfirmation.status,
                            )
                        ),
                        else_=None
                    )
                ).label("confirmed_by"),
            )
            .join(User, ChoreCompletion.completed_by_id == User.id)
            .join(Chore, ChoreCompletion.chore_id == Chore.id)
            .outerjoin(
                ChoreConfirmation,
                ChoreCompletion.id == ChoreConfirmation.chore_completion_id,
            )
            .outerjoin(confirm_user, ChoreConfirmation.user_id == confirm_user.id)
            .where(ChoreCompletion.id == chore_completion_id)
            .group_by(ChoreCompletion.id, Chore.id, User.id)
        )

        query_result = await self.db_session.execute(query)
        item = query_result.mappings().first()

        return NewChoreCompletionDetail.model_validate(item) if item else None
