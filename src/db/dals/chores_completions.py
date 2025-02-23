from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select

from core.base_dals import BaseDals
from core.constants import StatusConfirmENUM
from db.models.chore import ChoreCompletion, ChoreConfirmation


@dataclass
class AsyncChoreCompletionDAL(BaseDals):

    class Meta:
        model = ChoreCompletion


@dataclass
class AsyncChoreConfirmationDAL(BaseDals):

    class Meta:
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
    ) -> int:
        
        query = (
            select(func.count())
            .select_from(ChoreConfirmation)
            .where(
                ChoreConfirmation.chore_completion_id == chore_completion_id,
                ChoreConfirmation.status == status
            )
        )
        query_result = await self.db_session.execute(query)
        count = query_result.scalar()
        return count