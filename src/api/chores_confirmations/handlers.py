from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user_from_token
from db.session import get_db
from db.models.user import User
from schemas.chores.chores_confirmations import NewChoreConfirmationSetStatus
from schemas.chores.compositions import NewChoreConfirmationDetail
from services.chores.data import ChoreConfirmationDataService
from services.chores_completions.services import set_status_chore_confirmation
from api.chores_confirmations.permissions import (
    get_user_and_check_chore_confirmation_permission,
)


from logging import getLogger
logger = getLogger(__name__)

chores_confirmations_router = APIRouter()


# Get my chores confirmations
@chores_confirmations_router.get("")
async def get_my_chores_confirmations(
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db),
) -> list[NewChoreConfirmationDetail]:

    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        result = await data_service.get_user_chore_confirmations(current_user.id)
        return result


@chores_confirmations_router.patch("/{chore_confirmation_id}")
async def change_status_chore_confirmation(
    chore_confirmation_id: UUID,
    body: NewChoreConfirmationSetStatus,
    current_user: User = Depends(get_user_and_check_chore_confirmation_permission),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:

    async with async_session.begin():
        await set_status_chore_confirmation(
            chore_confirmation_id, body.status, async_session
        )

        return JSONResponse(content={"detail": "OK"}, status_code=201)
