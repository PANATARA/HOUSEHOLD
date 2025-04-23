from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chores_confirmations.schemas import ChoreConfirmationDetailSchema
from chores_confirmations.repository import ChoreConfirmationDataService
from chores_confirmations.services import set_status_chore_confirmation
from core.permissions import ChoreConfirmationPermission, IsAuthenicatedPermission
from core.enums import StatusConfirmENUM
from core.exceptions.base_exceptions import CanNotBeChangedError
from core.get_avatars import update_user_avatars
from database_connection import get_db
from chores_confirmations.schemas import ChoreConfirmationSetStatusSchema
from users.models import User


logger = getLogger(__name__)

chores_confirmations_router = APIRouter()


# Get my chores confirmations
@chores_confirmations_router.get(
    "",
    summary="Get all confirmation objects for chores completed by others and pending user's approval",
)
async def get_my_chores_confirmations(
    status: StatusConfirmENUM | None = None,  # by default we return all confirmations
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ChoreConfirmationDetailSchema]:
    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        result = await data_service.get_user_chore_confirmations(
            current_user.id, status
        )
        await update_user_avatars(result)
        return result


@chores_confirmations_router.patch("/{chore_confirmation_id}")
async def change_status_chore_confirmation(
    chore_confirmation_id: UUID,
    body: ChoreConfirmationSetStatusSchema,
    current_user: User = Depends(ChoreConfirmationPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        try:
            await set_status_chore_confirmation(
                chore_confirmation_id, body.status, async_session
            )
        except CanNotBeChangedError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{e}",
            )

    return JSONResponse(content={"detail": "OK"}, status_code=201)
