from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_completions.schemas import (
    ChoreCompletionDetailSchema,
    ChoreCompletionResponseSchema,
)
from chores_confirmations.models import ChoreConfirmation
from core.base_dals import BaseDals, GetOrRaiseMixin
from core.enums import StatusConfirmENUM
from core.exceptions.chores_completion import ChoreCompletionNotFoundError
from users.models import User


class AsyncChoreCompletionDAL(BaseDals[ChoreCompletion], GetOrRaiseMixin):
    model = ChoreCompletion
    not_found_exception = ChoreCompletionNotFoundError


@dataclass
class ChoreCompletionDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_chore_completion(
        self,
        family_id: UUID,
        offset: int,
        limit: int,
        status: StatusConfirmENUM | None,
        chore_id: UUID | None,
    ) -> list[ChoreCompletionResponseSchema]:
        """
        Retrieves a list of chore completion records for a specific family,
        including details of the completed chores and the users who completed them.

        Args:
            family_id (UUID): The ID of the family whose chore completions are to be fetched.
            offset (int): The number of records to skip for pagination.
            limit (int): The maximum number of records to retrieve.

        Returns:
            list[ChoreCompletionSchema]: A list of `ChoreCompletionSchema` Pydantic models
            representing the details of the completed chores, including chore information,
            the user who completed it, and the completion status.
        """

        conditions = [Chore.family_id == family_id]
        if status is not None:
            conditions.append(ChoreCompletion.status == status.value)
        if chore_id is not None:
            conditions.append(ChoreCompletion.chore_id == chore_id)

        query = (
            select(
                ChoreCompletion.id.label("id"),
                func.json_build_object(
                    "id",
                    Chore.id,
                    "name",
                    Chore.name,
                    "description",
                    Chore.description,
                    "icon",
                    Chore.icon,
                    "valuation",
                    Chore.valuation,
                ).label("chore"),
                func.json_build_object(
                    "id",
                    User.id,
                    "username",
                    User.username,
                    "name",
                    User.name,
                    "surname",
                    User.surname,
                ).label("completed_by"),
                ChoreCompletion.created_at.label("completed_at"),
                ChoreCompletion.status.label("status"),
                ChoreCompletion.message.label("message"),
            )
            .join(User, ChoreCompletion.completed_by_id == User.id)
            .join(Chore, ChoreCompletion.chore_id == Chore.id)
            .where(*conditions)
            .order_by(ChoreCompletion.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        chores_completions = [
            ChoreCompletionResponseSchema.model_validate(item) for item in raw_data
        ]
        return chores_completions

    async def get_family_chore_completion_detail(
        self, chore_completion_id: UUID
    ) -> ChoreCompletionDetailSchema | None:
        """
        Retrieves the detailed information for a specific chore completion,
        including the chore details, the user who completed it, and the users
        who have confirmed the completion.

        Args:
            chore_completion_id (UUID): The ID of the chore completion whose details are to be fetched.

        Returns:
            ChoreCompletionDetailSchema | None: A Pydantic model representing the details of the
            specified chore completion, including the chore, the user who completed it,
            the status, and the users who confirmed it. Returns None if no matching completion is found.
        """
        confirm_user = aliased(User)

        query = (
            select(
                func.json_build_object(
                    "id",
                    ChoreCompletion.id,
                    "chore",
                    func.json_build_object(
                        "id",
                        Chore.id,
                        "name",
                        Chore.name,
                        "description",
                        Chore.description,
                        "icon",
                        Chore.icon,
                        "valuation",
                        Chore.valuation,
                    ),
                    "completed_by",
                    func.json_build_object(
                        "id",
                        User.id,
                        "username",
                        User.username,
                        "name",
                        User.name,
                        "surname",
                        User.surname,
                    ),
                    "completed_at",
                    ChoreCompletion.created_at,
                    "message",
                    ChoreCompletion.message,
                    "status",
                    ChoreCompletion.status,
                ).label("chore_completion"),
                func.json_agg(
                    case(
                        (
                            ChoreConfirmation.id.isnot(None),
                            func.json_build_object(
                                "user",
                                func.json_build_object(
                                    "id",
                                    confirm_user.id,
                                    "username",
                                    confirm_user.username,
                                    "name",
                                    confirm_user.name,
                                    "surname",
                                    confirm_user.surname,
                                ),
                                "status",
                                ChoreConfirmation.status,
                            ),
                        ),
                        else_=None,
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

        return ChoreCompletionDetailSchema.model_validate(item) if item else None
