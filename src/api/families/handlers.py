from fastapi import APIRouter, Depends
from sqlalchemy import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.families.families_action import _add_user_to_family, _create_family, _get_family
from db.models.user import User
from db.session import get_db
from schemas.families import FamilyCreate, FamilyFullShow, FamilyShow 


from logging import getLogger
logger = getLogger(__name__)

families_router = APIRouter()

# Create a new family
@families_router.post("", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate, 
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyShow:
    
    return await _create_family(current_user, body, db)

# Get user family
@families_router.get("", response_model=FamilyFullShow)
async def get_my_family(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyFullShow:
    
    return await _get_family(current_user, db)

# Add user to family
@families_router.post(path="/add/user/{user_id}", summary="...Debug handler...")
async def add_user_to_family(
    user_id: str,
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> FamilyShow:
    
    return await _add_user_to_family(current_user.family_id, user_id, db)

# Logout user to family
@families_router.post(path="/logout", summary="NOT IMPLEMENTED")
async def add_user_to_family(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> None:
    
    return

@families_router.post(path="/kick/user/{user_id}", summary="NOT IMPLEMENTED")
async def kick_user_from_family(
    user_id: int,
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> None:
    
    return