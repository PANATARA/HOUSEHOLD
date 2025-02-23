from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.chores_logs.actions import _create_chore_log, _get_family_chorelog_detail, _get_family_chorelogs
from api.chores_logs.permissions import get_user_and_check_chorelog_permission
from db.models.user import User
from db.session import get_db
from schemas.chores_logs import ChoreLogCreate, ChoreLogDetailShow, ChoreLogShow


from logging import getLogger

logger = getLogger(__name__)

chores_logs_router = APIRouter()

# Create a new chorelog
@chores_logs_router.post("")
async def create_chore_log(
    body: ChoreLogCreate,
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> Response:
    
    return await _create_chore_log(
        body=body,
        user=current_user,
        async_session=db
    )

# Get family's chorelogs
@chores_logs_router.get("")
async def get_family_chorelogs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> list[ChoreLogShow]:
    
    return await _get_family_chorelogs(
        page=page,
        limit=limit,
        user=current_user,
        async_session=db
    )


# Get family's chorelog detail
@chores_logs_router.get("/{chorelog_id}")
async def get_family_chorelog_detail(
    chorelog_id: UUID,
    current_user: User = Depends(get_user_and_check_chorelog_permission), 
    db: AsyncSession = Depends(get_db)
) -> ChoreLogDetailShow:
    
    return await _get_family_chorelog_detail(
        chorelog_id=chorelog_id,
        user=current_user,
        async_session=db
    )