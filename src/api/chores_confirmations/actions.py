from uuid import UUID
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.chores_completions import NewChoreConfirmationDetail, NewChoreConfirmationSetStatus
from services.chores.data import ChoreConfirmationDataService
from services.chores_completions.services import set_status_chore_confirmation

from logging import getLogger
logger = getLogger(__name__)


async def _get_my_chores_confirmations(
    user: User, async_session: AsyncSession
) -> list[NewChoreConfirmationDetail]:
    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        result = await data_service.get_user_chore_confirmations(user.id)
        return result


async def _change_status_chore_confirmation(
    chore_confirmation_id: UUID,
    body: NewChoreConfirmationSetStatus,
    user: User,
    async_session: AsyncSession,
) -> JSONResponse:
    async with async_session.begin():
        await set_status_chore_confirmation(chore_confirmation_id, body.status, async_session)
        
        return JSONResponse(
            content={"detail": "OK"},
            status_code=201
        )
