from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_completions.repository import AsyncChoreCompletionDAL
from chores_confirmations.repository import AsyncChoreConfirmationDAL
from core.enums import StatusConfirmENUM
from core.services import BaseService
from core.validators import (
    validate_chore_completion_is_changable,
    validate_chore_is_active,
)
from families.repository import AsyncFamilyDAL
from users.models import User
from wallets.services import CoinsRewardService


@dataclass
class CreateChoreCompletion(BaseService[ChoreCompletion]):
    user: User
    chore: Chore
    message: str
    db_session: AsyncSession

    async def process(self) -> ChoreCompletion:
        status = StatusConfirmENUM.awaits
        users = await self._get_users_should_confirm_chore_completion()
        chore_completion = await self._create_chore_completion(status)

        if users is None:
            service = ApproveChoreCompletion(
                chore_completion=chore_completion, db_session=self.db_session
            )
            await service.run_process()
        else:
            await self._create_chores_confirmations(users, chore_completion.id)

        return chore_completion

    async def _create_chore_completion(self, status: str) -> ChoreCompletion:
        chore_completion_dal = AsyncChoreCompletionDAL(self.db_session)
        chore_completion = ChoreCompletion(
            family_id=self.chore.family_id,
            message=self.message,
            completed_by_id=self.user.id,
            chore_id=self.chore.id,
            status=status,
        )
        chore_completion = await chore_completion_dal.create(
            chore_completion
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

    def get_validators(self):
        return [lambda: validate_chore_is_active(self.chore)]


@dataclass
class ApproveChoreCompletion(BaseService[None]):
    chore_completion: ChoreCompletion
    db_session: AsyncSession

    async def process(self) -> None:
        await self.change_chore_completion_status()
        await self.send_reward()

    async def change_chore_completion_status(self):
        chore_completion_dal = AsyncChoreCompletionDAL(db_session=self.db_session)
        await chore_completion_dal.update(
            object_id=self.chore_completion.id,
            fields={"status": StatusConfirmENUM.approved},
        )

    async def send_reward(self):
        service = CoinsRewardService(
            chore_completion=self.chore_completion,
            message="income",
            db_session=self.db_session,
        )
        await service.run_process()

    def get_validators(self):
        return [lambda: validate_chore_completion_is_changable(self.chore_completion)]


@dataclass
class CancellChoreCompletion(BaseService[None]):
    chore_completion: ChoreCompletion
    db_session: AsyncSession

    async def process(self) -> None:
        await self.change_status_chore_completion()

    async def change_status_chore_completion(self) -> None:
        chore_completion_dal = AsyncChoreCompletionDAL(db_session=self.db_session)
        await chore_completion_dal.update(
            object_id=self.chore_completion.id,
            fields={"status": StatusConfirmENUM.canceled.value},
        )

    def get_validators(self):
        return [lambda: validate_chore_completion_is_changable(self.chore_completion)]
