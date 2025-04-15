from logging import getLogger

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.base_exceptions import ImageError
from core.permissions import IsAuthenicatedPermission
from core.get_avatars import update_user_avatars
from core.storage import PresignedUrl
from core.session import get_db
from users.aggregates import UserProfileSchema
from users.models import User
from users.repository import AsyncUserDAL, UserDataService
from users.schemas import (
    UserCreateSchema,
    UserSettingsShowSchema,
    UserSummarySchema,
    UserUpdateSchema,
)
from users.services import UserCreatorService, update_user_avatar
from wallets.repository import AsyncWalletDAL
from wallets.schemas import WalletBalanceSchema


logger = getLogger(__name__)


user_router = APIRouter()


# Create new User
@user_router.post("", response_model=UserSummarySchema)
async def create_user(
    body: UserCreateSchema, async_session: AsyncSession = Depends(get_db)
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
@user_router.get("",)
async def me_user_get(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserProfileSchema:
    async with async_session.begin():
        wallet = await AsyncWalletDAL(async_session).get_by_user_id(current_user.id)
    
    result = UserProfileSchema(
        user=UserSummarySchema(
            id=current_user.id,
            username=current_user.username,
            name=current_user.name,
            surname=current_user.surname,
        ),
        wallet=WalletBalanceSchema(
            id=wallet.id,
            balance=wallet.balance,
        ) if wallet else None
    )
    await update_user_avatars(result)
    return result


# Update user
@user_router.patch("", response_model=UserSummarySchema)
async def me__user_partial_update(
    body: UserUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSummarySchema:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            object_id=current_user.id, fields=body.model_dump()
        )
    result = UserSummarySchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )
    await update_user_avatars(result)
    return result


# Get user's settings
@user_router.get(
    "/settings", response_model=UserSettingsShowSchema, summary="Get me settings"
)
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsShowSchema:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(user_id=current_user.id)


@user_router.post("/avatar/file/")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(IsAuthenicatedPermission()),
) -> PresignedUrl:
    
    try:
        avatar_url = await update_user_avatar(current_user, file)
    except ImageError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    return avatar_url
    