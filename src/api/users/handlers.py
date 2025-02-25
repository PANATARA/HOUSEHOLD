from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.users.users_actions import _create_new_user, _get_me_settings, _update_user, show_user
from schemas.users import UserDetail, UserResponse, UserCreate, UserSettingsShow, UserUpdate
from db.models.user import User
from db.session import get_db
from logging import getLogger

logger = getLogger(__name__)

user_router = APIRouter()

# Create new User
@user_router.post("/", response_model=UserResponse)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    try:
        return await _create_new_user(body, db)
    except IntegrityError as err:
        logger.error(err)
        raise HTTPException(status_code=503, detail=f"Database error: {err}")

# Get user's profile (all info)
@user_router.get("/me", response_model=UserDetail)
async def me_user_get(
    current_user: User = Depends(get_current_user_from_token)
) -> UserDetail:
    return await show_user(current_user)


@user_router.patch("/", response_model=UserResponse)
async def me__user_partial_update(
    body: UserUpdate, 
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    
    return await _update_user(
        user=current_user, 
        body=body, 
        async_session=db
    )


@user_router.delete("/")
async def me_user_delete( 
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> None:
    return


#Get user's settings
@user_router.get("/me/settings", response_model=UserSettingsShow, summary="Get me settings")
async def me_user_get_settings(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> UserSettingsShow:
    
    return await _get_me_settings(current_user, db)