from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.chores_confirmations.actions import _change_status_chorelog_confirmation, _get_my_chores_confirmations
from api.chores_confirmations.permissions import get_user_and_check_confirm_chorelog_permission
from db.models.user import User
from db.session import get_db


from logging import getLogger

from schemas.chores_logs import ChoreConfirmation, ChoreLogConfirmation, ChoreLogConfirmationChangeStatus

logger = getLogger(__name__)

chores_confirmations = APIRouter()

# Get my chores confirmations
@chores_confirmations.get("")
async def get_my_chores_confirmations(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> list[ChoreConfirmation]:
    
    return await _get_my_chores_confirmations(
        user=current_user,
        async_session=db
    )

@chores_confirmations.patch("/{chorlog_id}")
async def change_status_chorelog_confirmation(
    confirm_chorlog_id: UUID,
    body: ChoreLogConfirmationChangeStatus,
    current_user: User = Depends(get_user_and_check_confirm_chorelog_permission), 
    db: AsyncSession = Depends(get_db)
) -> None:
    
    return await _change_status_chorelog_confirmation(
        chorelog_confirm=confirm_chorlog_id,
        body=body,
        user=current_user,
        async_session=db
    )