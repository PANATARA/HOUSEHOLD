from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import StatusConfirmENUM
from core.services import BaseService
from db.dals.chores_logs import AsyncChoreLogConfirmDAL, AsyncChoreLogDAL
from db.dals.families import AsyncFamilyDAL
from db.models.chore import Chore, ChoreLog
from db.models.user import User
from services.wallets.services import CoinsCreditService


@dataclass
class CreateChoreLog(BaseService):

    user: User
    chore_id: Chore | UUID
    message: str
    db_session: AsyncSession

    async def execute(self) -> ChoreLog:
        status = StatusConfirmENUM.awaits.value
        users = await self._get_users_should_confirm_chorelog()
        chore_log = await self._create_chore_log(status)

        if users is None:
            service = ApproveChoreLog(chore_log_id=chore_log.id, db_session=self.db_session)
            await service()
        else:
            await self._create_chorelog_confirm(users, chore_log.id)

        return chore_log

    async def _create_chore_log(self, status: str) -> ChoreLog:
        chore_log_dal = AsyncChoreLogDAL(self.db_session)
        chore_log = await chore_log_dal.create(
            fields={
                "message": self.message,
                "completed_by_id": self.user.id,
                "chore_id": self.chore_id,
                "status": status,
            }
        )
        return chore_log

    async def _get_users_should_confirm_chorelog(self) -> list[UUID] | None:
        family_dal = AsyncFamilyDAL(self.db_session)
        family_admins = await family_dal.get_users_should_confirm_chorelog(
            self.user.family_id, excluded_user_ids=[self.user.id]
        )
        return family_admins

    async def _create_chorelog_confirm(
        self, users_ids: list[UUID], chorelog_id: UUID
    ) -> None:
        if users_ids is None:
            return

        chorelog_confirm_dal = AsyncChoreLogConfirmDAL(self.db_session)
        await chorelog_confirm_dal.create_choreslogs_confirm_many(
            users_ids=users_ids, chorelog_id=chorelog_id
        )

    async def validate(self):
        return


@dataclass
class ApproveChoreLog(BaseService):
    chore_log_id: UUID
    db_session: AsyncSession

    async def execute(self) -> None:
        await self.change_chorelog_status()
        await self.send_reward()

    async def change_chorelog_status(self):
        chorelog_dal = AsyncChoreLogDAL(db_session=self.db_session)
        await chorelog_dal.update(
            object_id=self.chore_log_id,
            fields={"status": StatusConfirmENUM.approved.value}
        )

    async def send_reward(self):
        chorelog = await AsyncChoreLogDAL(self.db_session).get_by_id(self.chore_log_id)
        service = CoinsCreditService(
            chorelog=chorelog,
            message="income",
            db_session=self.db_session,
        )
        await service()

    async def validate(self):
        return


@dataclass
class CancellChoreLog(BaseService):
    chore_log_id: UUID
    db_session: AsyncSession

    async def execute(self) -> None:
        await self.change_chorelog_status()

    async def change_chorelog_status(self) -> None:
        chorelog_dal = AsyncChoreLogDAL(db_session=self.db_session)
        await chorelog_dal.update(
            object_id=self.chore_log_id,
            fields={"status": StatusConfirmENUM.canceled.value}
        )

    async def validate(self):
        return


async def set_status_confirm_chorelog(chorelog_confirm: UUID, message: str, status: int):
    pass