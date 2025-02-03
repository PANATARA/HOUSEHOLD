from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.chores.chores_action import _get_family_chore
from db.models.user import User
from db.session import get_db
from schemas.chores import ChoresResponse


from logging import getLogger
logger = getLogger(__name__)

chores_router = APIRouter()


@chores_router.get("", response_model=ChoresResponse)
async def get_family_chore(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> ChoresResponse:
    
    return await _get_family_chore(current_user.family_id, db)