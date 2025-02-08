from dataclasses import dataclass
from uuid import UUID

from core.base_dals import BaseDals
from db.models.chore import Chore, ChoreLogConfirm


@dataclass
class AsyncChoreLogDAL(BaseDals):

    class Meta:
        model = Chore


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
                status=0,
            )
            for user_id in users_ids
        ]

        self.db_session.add_all(chorelog_confirms)
        await self.db_session.flush()
        return None
