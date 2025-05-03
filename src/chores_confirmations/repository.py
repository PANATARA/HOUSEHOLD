from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_confirmations.models import ChoreConfirmation
from chores_confirmations.schemas import ChoreConfirmationResponseSchema
from core.base_dals import BaseDals
from core.enums import StatusConfirmENUM
from users.models import User


class AsyncChoreConfirmationDAL(BaseDals[ChoreConfirmation]):

    model = ChoreConfirmation

    async def create_many_chore_confirmation(
        self, users_ids: list[UUID], chore_completion_id: UUID
    ) -> None:

        chores_confirmations = [
            ChoreConfirmation(
                chore_completion_id=chore_completion_id,
                user_id=user_id,
                status=StatusConfirmENUM.awaits.value,
            )
            for user_id in users_ids
        ]

        self.db_session.add_all(chores_confirmations)
        await self.db_session.flush()
        return None

    async def count_status_chore_confirmation(
        self, chore_completion_id: UUID, status: StatusConfirmENUM
    ) -> int | None:

        query = (
            select(func.count())
            .select_from(ChoreConfirmation)
            .where(
                ChoreConfirmation.chore_completion_id == chore_completion_id,
                ChoreConfirmation.status == status,
            )
        )
        query_result = await self.db_session.execute(query)
        count = query_result.scalar()
        return count


@dataclass
class ChoreConfirmationDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_user_chore_confirmations(
        self, user_id: UUID, status: StatusConfirmENUM | None
    ) -> list[ChoreConfirmationResponseSchema]:
        """
        Fetches the list of chore confirmations for a specific user.

        This method retrieves the details of chore confirmations made by the specified user, including
        information about the completed chore, the user who completed it, the completion status,
        and the confirmation status.

        Args:
            user_id (UUID): The unique identifier of the user whose chore confirmations are being fetched.

        Returns:
            list[ChoreConfirmationDetailSchema]: A list of chore confirmation details for the specified user.
            Returns None if no confirmations are found.
        """

        conditions = [ChoreConfirmation.user_id == user_id]
        if status is not None:
            conditions.append(ChoreConfirmation.status == status)

        query = (
            select(
                ChoreConfirmation.id.label("id"),
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
                    "status",
                    ChoreCompletion.status,
                    "message",
                    ChoreCompletion.message,
                ).label("chore_completion"),
                ChoreConfirmation.created_at.label("created_at"),
                ChoreConfirmation.status.label("status"),
            )
            .join(
                ChoreCompletion,
                ChoreConfirmation.chore_completion_id == ChoreCompletion.id,
            )
            .join(Chore, ChoreCompletion.chore_id == Chore.id)
            .join(User, ChoreCompletion.completed_by_id == User.id)
            .where(*conditions)
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        confirmations = [
            ChoreConfirmationResponseSchema.model_validate(item) for item in raw_data
        ]

        return confirmations
