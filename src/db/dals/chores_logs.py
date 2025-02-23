from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select

from core.base_dals import BaseDals
from core.constants import StatusConfirmENUM
from db.models.chore import Chore, ChoreLog, ChoreLogConfirm


@dataclass
class AsyncChoreLogDAL(BaseDals):

    class Meta:
        model = ChoreLog


@dataclass
class AsyncChoreLogConfirmDAL(BaseDals):

    class Meta:
        model = ChoreLogConfirm

    async def create_choreslogs_confirm_many(
        self, users_ids: list[UUID], chorelog_id: UUID
    ) -> None:

        chorelog_confirms = [
            ChoreLogConfirm(
                chore_log_id=chorelog_id,
                user_id=user_id,
                status=StatusConfirmENUM.awaits.value,
            )
            for user_id in users_ids
        ]

        self.db_session.add_all(chorelog_confirms)
        await self.db_session.flush()
        return None

    async def count_choreslogs_confirmations_status(
        self, chorelog_id: UUID, status: StatusConfirmENUM
    ) -> int:
        
        query = (
            select(func.count())
            .select_from(ChoreLogConfirm)
            .where(
                ChoreLogConfirm.chore_log_id == chorelog_id,
                ChoreLogConfirm.status == status
            )
        )
        query_result = await self.db_session.execute(query)
        count = query_result.scalar()
        return count