from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.families.families_action import _create_family, _get_family
from db.models.user import User
from db.session import get_db
from logging import getLogger

from schemas.families import FamilyCreate, FamilyFullShow, FamilyShow
from services.family_chore import get_default_chore_data

logger = getLogger(__name__)

families_router = APIRouter()

@families_router.post("", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate, 
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyShow:
    
    return await _create_family(current_user, body, db)

@families_router.get("", response_model=FamilyFullShow)
async def get_my_family(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyFullShow:
    
    return await _get_family(current_user, db)