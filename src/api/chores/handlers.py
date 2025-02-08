from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.chores.chores_action import _create_family_chore, _get_family_chore
from db.models.user import User
from db.session import get_db
from schemas.chores import ChoreCreate, ChoreShow, ChoresResponse


from logging import getLogger

logger = getLogger(__name__)

chores_router = APIRouter()


# List of all family  chores
@chores_router.get("", response_model=ChoresResponse)
async def get_family_chore(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> ChoresResponse:

    return await _get_family_chore(current_user.family_id, db)

# Create a new family  chore
@chores_router.post("", response_model=ChoreShow)
async def create_family_chore(
    body: ChoreCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> ChoreShow:
    return await _create_family_chore(
        body=body, family_id=current_user.family_id, async_session=db
    )


# Delete family chore
@chores_router.delete(path="/{chore_id}", summary="NOT IMPLEMENTED")
async def delete_family_chore(
    chore_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:

    return


# Update family chore
@chores_router.patch(path="/{chore_id}", summary="NOT IMPLEMENTED")
async def update_family_chore(
    chore_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:

    return
