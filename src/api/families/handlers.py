from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.families.families_action import _create_family
from db.models.user import User
from db.session import get_db
from logging import getLogger

from schemas.families import FamilyCreate, FamilyShow

logger = getLogger(__name__)

families_router = APIRouter()

@families_router.post("/", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate, 
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyShow:
    
    return await _create_family(current_user, body, db)
