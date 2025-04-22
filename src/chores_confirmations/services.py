from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores_completions.repository import AsyncChoreCompletionDAL
from chores_completions.services import ApproveChoreCompletion, CancellChoreCompletion
from chores_confirmations.repository import AsyncChoreConfirmationDAL
from core.enums import StatusConfirmENUM


async def set_status_chore_confirmation(
    chore_confirmation_id: UUID, status: StatusConfirmENUM, db_session: AsyncSession
) -> None:
    chore_confirmation_dal = AsyncChoreConfirmationDAL(db_session)
    chore_confirmation = await chore_confirmation_dal.update(
        object_id=chore_confirmation_id, fields={"status": status}
    )
    chore_completion_dal = AsyncChoreCompletionDAL(db_session=db_session)
    chore_completion = await chore_completion_dal.get_or_raise(
        chore_confirmation.chore_completion_id
    )
    if status == StatusConfirmENUM.canceled:
        service = CancellChoreCompletion(
            chore_completion=chore_completion, db_session=db_session
        )
        await service.run_process()
    elif status == StatusConfirmENUM.approved:
        count_chores_confirmations = (
            await chore_confirmation_dal.count_status_chore_confirmation(
                chore_completion_id=chore_confirmation.chore_completion_id,
                status=StatusConfirmENUM.awaits,
            )
        )
        if count_chores_confirmations == 0:
            service = ApproveChoreCompletion(
                chore_completion=chore_completion, db_session=db_session
            )
            await service.run_process()
