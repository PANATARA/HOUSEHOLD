from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import ChoreConfirmationPermission, IsAuthenicatedPermission
from core.constants import StatusConfirmENUM
from db.models.user import User
from db.session import get_db
from schemas.chores.chores_confirmations import NewChoreConfirmationSetStatus
from schemas.chores.compositions import NewChoreConfirmationDetail
from services.chores.data import ChoreConfirmationDataService
from services.chores_completions.services import set_status_chore_confirmation

logger = getLogger(__name__)

chores_confirmations_router = APIRouter()


# Get my chores confirmations
@chores_confirmations_router.get("")
async def get_my_chores_confirmations(
    status: StatusConfirmENUM | None = None, # by default we return unprocessed confirmations
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[NewChoreConfirmationDetail]:

    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        print(f"ВОТ ЗНАЧЕНИЕ СТАТУСА {status}")
        result = await data_service.get_user_chore_confirmations(current_user.id, status)
        return result


@chores_confirmations_router.patch("/{chore_confirmation_id}")
async def change_status_chore_confirmation(
    chore_confirmation_id: UUID,
    body: NewChoreConfirmationSetStatus,
    current_user: User = Depends(ChoreConfirmationPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:

    async with async_session.begin():
        await set_status_chore_confirmation(
            chore_confirmation_id, body.status, async_session
        )

        return JSONResponse(content={"detail": "OK"}, status_code=201)
