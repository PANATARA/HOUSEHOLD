from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import ChoreCompletionPermission, IsAuthenicatedPermission
from db.models.user import User
from db.session import get_db
from schemas.chores.chores_completions import NewChoreCompletionCreate, NewChoreCompletionSummary
from schemas.chores.compositions import NewChoreCompletionDetail
from services.chores_completions.services import CreateChoreCompletion
from services.chores_completions.data import ChoreCompletionDataService


from logging import getLogger
logger = getLogger(__name__)

chores_completions_router = APIRouter()

# Create a new chore completion
@chores_completions_router.post(path="/{chore-id}")
async def create_chore_completion(
    chore_id: UUID,
    body: NewChoreCompletionCreate,
    current_user: User = Depends(IsAuthenicatedPermission()), 
    async_session: AsyncSession = Depends(get_db)
) -> Response:
    
    async with async_session.begin():
        creator_service = CreateChoreCompletion(
            user=current_user,
            chore_id=chore_id,
            message=body.message,
            db_session=async_session,
        )
        await creator_service.run_process()
    return Response(
        status_code=204,
    )

# Get family's chores completions
@chores_completions_router.get("")
async def get_family_chores_completions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=50),
    current_user: User = Depends(IsAuthenicatedPermission()), 
    async_session: AsyncSession = Depends(get_db)
) -> list[NewChoreCompletionSummary]:
    
    async with async_session.begin():
        offset = (page - 1) * limit
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion(current_user.family_id, offset, limit)
        return result


# Get family's chore completion detail
@chores_completions_router.get("/{chore_completion_id}")
async def get_family_chore_completion_detail(
    chore_completion_id: UUID,
    current_user: User = Depends(ChoreCompletionPermission()), 
    async_session: AsyncSession = Depends(get_db)
) -> NewChoreCompletionDetail:
    
    async with async_session.begin():
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion_detail(chore_completion_id)
        return result