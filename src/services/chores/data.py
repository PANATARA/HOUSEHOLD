from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.constants import StatusConfirmENUM
from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.models.user import User
from schemas.chores.chores import ChoreSchema
from schemas.chores.compositions import NewChoreConfirmationDetail, NewChoreDetailMax


@dataclass
class ChoreDataService:
    db_session: AsyncSession

    async def get_family_chores(self, family_id: UUID) -> list[ChoreSchema] | None:
        """
        Retrieves a list of chores associated with a specific family.

        Args:
            family_id (UUID): The ID of the family whose chores are being fetched.

        Returns:
            list[ChioreSchema] | None: A list of chores if found, otherwise None.
        """
        query = select(
            Chore.id,
            Chore.name,
            Chore.description,
            Chore.icon,
            Chore.valuation,
        ).where(Chore.family_id == family_id)

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        if not raw_data:
            return None

        return [ChoreSchema.model_validate(item) for item in raw_data]

    async def get_family_chore_with_chore_completions(
        self, chore_id: UUID, limit: int, offset: int
    ) -> NewChoreDetailMax:
        """
        Fetches a family chore along with its completion details.

        Args:
            chore_id (UUID): The ID of the chore to retrieve.
            limit (int): The maximum number of chore completions to return.
            offset (int): The pagination offset.

        Returns:
            NewChoreDetailMax: The chore details with associated completions.
        """
        query = (
            select(
                Chore.id,
                Chore.name,
                Chore.description,
                Chore.icon,
                Chore.valuation,
                Chore.created_at,
                func.json_agg(
                    case(
                        (
                            ChoreCompletion.id.isnot(None),
                            func.json_build_object(
                                "id",
                                ChoreCompletion.id,
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
                            ),
                        ),
                        else_=None,
                    )
                ).label("chores_completion"),
            )
            .select_from(Chore)
            .join(ChoreCompletion, ChoreCompletion.chore_id == Chore.id, isouter=True)
            .join(User, User.id == ChoreCompletion.completed_by_id, isouter=True)
            .where(Chore.id == chore_id)
            .group_by(Chore.id)
            .limit(limit)
            .offset(offset)
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        chores_details = NewChoreDetailMax.model_validate(raw_data[0])

        return chores_details


@dataclass
class ChoreConfirmationDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_user_chore_confirmations(
        self, user_id: UUID, status: StatusConfirmENUM | None
    ) -> list[NewChoreConfirmationDetail]:
        """
        Fetches the list of chore confirmations for a specific user.

        This method retrieves the details of chore confirmations made by the specified user, including
        information about the completed chore, the user who completed it, the completion status,
        and the confirmation status.

        Args:
            user_id (UUID): The unique identifier of the user whose chore confirmations are being fetched.

        Returns:
            list[NewChoreConfirmationDetail]: A list of chore confirmation details for the specified user.
            Returns None if no confirmations are found.
        """

        conditions = [ChoreConfirmation.user_id == user_id]
        if status is not None:
            conditions.append(ChoreConfirmation.status==status)

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
            .join(ChoreCompletion, ChoreConfirmation.chore_completion_id == ChoreCompletion.id)
            .join(Chore, ChoreCompletion.chore_id == Chore.id)
            .join(User, ChoreCompletion.completed_by_id == User.id)
            .where(*conditions)
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        confirmations = [
            NewChoreConfirmationDetail.model_validate(item) for item in raw_data
        ]

        return confirmations
