from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import ChoreLogEnum
from core.services import BaseService
from db.dals.chores_logs import AsyncChoreLogConfirmDAL, AsyncChoreLogDAL
from db.dals.families import AsyncFamilyDAL
from db.models.chore import Chore, ChoreLog
from db.models.family import Family
from db.models.user import User


@dataclass
class CreateChoreLog(BaseService):

    user: User
    chore_id: Chore | UUID
    message: str
    db_session: AsyncSession

    async def execute(self) -> Family:
        status = await self._get_status()
        chore_log = await self._create_chore_log(status)
        family_admins_ids = await self._get_family_admins()
        await self._create_chorelog_confirm(family_admins_ids, chore_log.id)
        return chore_log

    async def _get_status() -> int:
        return ChoreLogEnum.awaiting_confirmation.value

    async def _create_chore_log(self, status: int) -> ChoreLog:
        chore_log_dal = AsyncChoreLogDAL(self.db_session)
        chore_log = await chore_log_dal.create(
            fields={
                "message": self.message,
                "completed_by_id": self.user,
                "chore_id": self.chore_id,
                "status": status,
            }
        )
        return chore_log

    async def _get_family_admins(self) -> list[UUID]:
        family_dal = AsyncFamilyDAL(self.db_session)
        family_admins = await family_dal.get_family_admins(self.user.family_id)
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
class ConfirmChoreLog(BaseService):
    chore_log_id: UUID
    db_session: AsyncSession

    async def execute(self) -> None:
        pass

    async def change_chorelog_status():
        pass

    async def send_reward():
        pass

    async def validate(self):
        return


@dataclass
class CancellChoreLog(BaseService):
    chore_log_id: UUID
    db_session: AsyncSession

    async def execute(self) -> None:
        pass

    async def validate(self):
        return
