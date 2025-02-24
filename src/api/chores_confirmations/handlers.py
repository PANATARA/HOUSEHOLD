from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models.user import User
from api.auth.auth_actions import get_current_user_from_token
from api.chores_confirmations.actions import (
    _change_status_chore_confirmation,
    _get_my_chores_confirmations,
)
from api.chores_confirmations.permissions import (
    get_user_and_check_chore_confirmation_permission,
)
from schemas.chores_completions import (
    NewChoreConfirmationDetail,
    NewChoreConfirmationSetStatus,
)


from logging import getLogger


logger = getLogger(__name__)

chores_confirmations = APIRouter()


# Get my chores confirmations
@chores_confirmations.get("")
async def get_my_chores_confirmations(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[NewChoreConfirmationDetail]:

    return await _get_my_chores_confirmations(user=current_user, async_session=db)


@chores_confirmations.patch("/{chore_confirmation_id}")
async def change_status_chore_confirmation(
    chore_confirmation_id: UUID,
    body: NewChoreConfirmationSetStatus,
    current_user: User = Depends(get_user_and_check_chore_confirmation_permission),
    db: AsyncSession = Depends(get_db),
) -> None:

    return await _change_status_chore_confirmation(
        chore_confirmation_id=chore_confirmation_id,
        body=body,
        user=current_user,
        async_session=db,
    )
