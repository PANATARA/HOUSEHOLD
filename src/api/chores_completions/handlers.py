from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.chores_completions.actions import _create_chore_completion, _get_family_chore_completion_detail, _get_family_chores_completions
from api.chores_completions.permissions import get_user_and_check_chore_completion_permission
from db.models.user import User
from db.session import get_db
from schemas.chores_completions import NewChoreCompletionCreate, NewChoreCompletionDetail, NewChoreCompletionSummary


from logging import getLogger

logger = getLogger(__name__)

chores_completions_router = APIRouter()

# Create a new chore completion
@chores_completions_router.post("")
async def create_chore_completion(
    body: NewChoreCompletionCreate,
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> Response:
    
    return await _create_chore_completion(
        body=body,
        user=current_user,
        async_session=db
    )

# Get family's chores completions
@chores_completions_router.get("")
async def get_family_chores_completions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> list[NewChoreCompletionSummary]:
    
    return await _get_family_chores_completions(
        page=page,
        limit=limit,
        user=current_user,
        async_session=db
    )


# Get family's chore completion detail
@chores_completions_router.get("/{chore_completion_id}")
async def get_family_chore_completion_detail(
    chore_completion_id: UUID,
    current_user: User = Depends(get_user_and_check_chore_completion_permission), 
    db: AsyncSession = Depends(get_db)
) -> NewChoreCompletionDetail:
    
    return await _get_family_chore_completion_detail(
        chore_completion_id=chore_completion_id,
        user=current_user,
        async_session=db
    )