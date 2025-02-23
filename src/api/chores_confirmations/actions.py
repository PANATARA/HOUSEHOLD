from uuid import UUID
from fastapi import Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.chores_logs import ChoreConfirmation, ChoreLogConfirmationChangeStatus


from logging import getLogger

from services.chores.data import ChoreConfirmationDataService
from services.chores_logs.services import set_status_confirm_chorelog

logger = getLogger(__name__)


async def _get_my_chores_confirmations(
    user: User, async_session: AsyncSession
) -> list[ChoreConfirmation]:
    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        result = await data_service.get_user_chore_confirmations(user.id)
        return result


async def _change_status_chorelog_confirmation(
    chorelog_confirm: UUID,
    body: ChoreLogConfirmationChangeStatus,
    user: User,
    async_session: AsyncSession,
) -> JSONResponse:
    async with async_session.begin():
        await set_status_confirm_chorelog(chorelog_confirm, body.status, async_session)
        
        return JSONResponse(
            content={"detail": "OK"},
            status_code=201
        )
