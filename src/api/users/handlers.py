from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import IsAuthenicatedPermission
from db.dals.users import AsyncUserDAL
from db.models.user import User
from db.session import get_db
from schemas.users import (
    UserCreate,
    UserSettingsShow,
    UserSummarySchema,
    UserUpdate,
)
from services.users.data import UserDataService
from services.users.services import UserCreatorService

logger = getLogger(__name__)


user_router = APIRouter()


# Create new User
@user_router.post("/", response_model=UserSummarySchema)
async def create_user(
    body: UserCreate, async_session: AsyncSession = Depends(get_db)
) -> UserSummarySchema:
    async with async_session.begin():
        try:
            service = UserCreatorService(
                username=body.username,
                name=body.name,
                surname=body.surname,
                password=body.password,
                db_session=async_session,
            )
            user = await service.run_process()
        except IntegrityError as err:
            logger.error(err)
            raise HTTPException(status_code=503, detail=f"Database error: {err}")

    return UserSummarySchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )


# # Get user's profile (all info)
@user_router.get(
    "/me",
)
async def me_user_get(
    current_user: User = Depends(IsAuthenicatedPermission()),
) -> UserSummarySchema:
    return UserSummarySchema(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        surname=current_user.surname,
    )


# Update user
@user_router.patch("/me", response_model=UserSummarySchema)
async def me__user_partial_update(
    body: UserUpdate,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSummarySchema:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            object_id=current_user.id, fields=body.model_dump()
        )
    return UserSummarySchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )


# Get user's settings
@user_router.get(
    "/me/settings", response_model=UserSettingsShow, summary="Get me settings"
)
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsShow:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(user_id=current_user.id)
