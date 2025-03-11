from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import StatusConfirmENUM
from core.exceptions import ChoreCompletionCanNotBeChanged, ChoreNotFoundError
from core.services import BaseService
from db.dals.chores_completions import AsyncChoreConfirmationDAL, AsyncChoreCompletionDAL
from db.dals.families import AsyncFamilyDAL
from db.models.chore import Chore, ChoreCompletion
from db.models.user import User
from services.wallets.services import CoinsRewardService


@dataclass
class CreateChoreCompletion(BaseService):

    user: User
    chore: Chore
    message: str
    db_session: AsyncSession

    async def process(self) -> ChoreCompletion:
        status = StatusConfirmENUM.awaits.value
        users = await self._get_users_should_confirm_chore_completion()
        chore_completion = await self._create_chore_completion(status)

        if users is None:
            service = ApproveChoreCompletion(chore_completion=chore_completion, db_session=self.db_session)
            await service.run_process()
        else:
            await self._create_chores_confirmations(users, chore_completion.id)

        return chore_completion

    async def _create_chore_completion(self, status: str) -> ChoreCompletion:
        chore_completion_dal = AsyncChoreCompletionDAL(self.db_session)
        chore_completion = await chore_completion_dal.create(
            fields={
                "message": self.message,
                "completed_by_id": self.user.id,
                "chore_id": self.chore.id,
                "status": status,
            }
        )
        return chore_completion

    async def _get_users_should_confirm_chore_completion(self) -> list[UUID] | None:
        family_dal = AsyncFamilyDAL(self.db_session)
        family_admins = await family_dal.get_users_should_confirm_chore_completion(
            self.user.family_id, excluded_user_ids=[self.user.id]
        )
        return family_admins

    async def _create_chores_confirmations(
        self, users_ids: list[UUID], chore_completion_id: UUID
    ) -> None:
        if users_ids is None:
            return

        chore_confirmation_dal = AsyncChoreConfirmationDAL(self.db_session)
        await chore_confirmation_dal.create_many_chore_confirmation(
            users_ids=users_ids, chore_completion_id=chore_completion_id
        )

    def validate(self):
        if not self.chore.is_active:
            raise ChoreNotFoundError()


@dataclass
class ApproveChoreCompletion(BaseService):
    chore_completion: ChoreCompletion
    db_session: AsyncSession

    async def process(self) -> None:
        await self.change_chore_completion_status()
        await self.send_reward()

    async def change_chore_completion_status(self):
        chore_completion_dal = AsyncChoreCompletionDAL(db_session=self.db_session)
        await chore_completion_dal.update(
            object_id=self.chore_completion.id,
            fields={"status": StatusConfirmENUM.approved.value}
        )

    async def send_reward(self):
        service = CoinsRewardService(
            chore_completion=self.chore_completion,
            message="income",
            db_session=self.db_session,
        )
        await service.run_process()

    def validate(self):
        if self.chore_completion.status != StatusConfirmENUM.awaits:
            raise ChoreCompletionCanNotBeChanged()


@dataclass
class CancellChoreCompletion(BaseService):
    chore_completion: UUID
    db_session: AsyncSession

    async def process(self) -> None:
        await self.change_status_chore_completion()

    async def change_status_chore_completion(self) -> None:
        chore_completion_dal = AsyncChoreCompletionDAL(db_session=self.db_session)
        await chore_completion_dal.update(
            object_id=self.chore_completion_id,
            fields={"status": StatusConfirmENUM.canceled.value}
        )

    def validate(self):
        if self.chore_completion.status != StatusConfirmENUM.awaits:
            raise ChoreCompletionCanNotBeChanged()


async def set_status_chore_confirmation(
    chore_confirmation_id: UUID, status: StatusConfirmENUM, db_session: AsyncSession
) -> None:
    chore_confirmation_dal = AsyncChoreConfirmationDAL(db_session)
    chore_confirmation = await chore_confirmation_dal.update(
        object_id=chore_confirmation_id,
        fields={
            "status": status
        }
    )
    chore_completion_dal = AsyncChoreCompletionDAL(db_session=db_session)
    chore_completion = chore_completion_dal.get_by_id(
        chore_confirmation.chore_completion_id
    ) 
    if status == StatusConfirmENUM.canceled.value:
        service = CancellChoreCompletion(
                chore_completion=chore_completion,
                db_session=db_session
            )
        await service.run_process()
    else:    
        count_chores_confirmations = await chore_confirmation_dal.count_status_chore_confirmation(
            chore_completion_id=chore_confirmation.chore_completion_id,
            status=StatusConfirmENUM.awaits.value
        )
        if count_chores_confirmations == 0:
            service = ApproveChoreCompletion(
                chore_completion=chore_completion,
                db_session=db_session
            )
            await service.run_process()
