from datetime import datetime, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.base_exceptions import ImageError
from core.exceptions.users import UserError, UserNotFoundError
from core.get_avatars import update_user_avatars, upload_object_image
from metrics import ActivitiesResponse, DateRangeSchema, get_user_activity
from core.permissions import FamilyMemberPermission, IsAuthenicatedPermission
from database_connection import get_db
from users.aggregates import MeProfileSchema, UserProfileSchema
from users.models import User
from users.repository import AsyncUserDAL, UserDataService
from users.schemas import (
    UserCreateSchema,
    UserSettingsResponseSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from users.services import UserCreatorService
from wallets.repository import AsyncWalletDAL
from wallets.schemas import WalletBalanceSchema

logger = getLogger(__name__)


router = APIRouter()


# Create new User
@router.post(
    "",
    tags=["Users"],
    summary="Create new user, user's settings and set default user avatar",
)
async def create_new_user(
    body: UserCreateSchema, async_session: AsyncSession = Depends(get_db)
) -> UserResponseSchema:
    async with async_session.begin():
        try:
            service = UserCreatorService(
                user_data=body,
                db_session=async_session,
            )
            user = await service.run_process()
        except UserError as err:
            raise HTTPException(status_code=400, detail=f"Error: {err}")

    user_response = UserResponseSchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )
    await update_user_avatars(user_response)
    return user_response


# Get user's profile (all info)
@router.get("", summary="Getting user's profile info", tags=["Users"])
async def me_get_user_profile(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> MeProfileSchema:
    async with async_session.begin():
        wallet = await AsyncWalletDAL(async_session).get_by_user_id(current_user.id)

    user_response = UserResponseSchema(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        surname=current_user.surname,
    )
    await update_user_avatars(user_response)

    wallet_response = (
        WalletBalanceSchema(
            balance=wallet.balance,
        )
        if wallet
        else None
    )

    result_response = MeProfileSchema(
        user=user_response,
        is_family_member=bool(current_user.family_id),
        wallet=wallet_response,
    )

    return result_response


# Update user
@router.patch("", tags=["Users"])
async def me_user_partial_update(
    body: UserUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            object_id=current_user.id, fields=body.model_dump(exclude_unset=True)
        )
    result_response = UserResponseSchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )
    await update_user_avatars(result_response)
    return result_response


# Get user's settings
@router.get("/settings", summary="Getting user settings", tags=["Users settings"])
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsResponseSchema:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(user_id=current_user.id)


@router.post("/avatar/file", summary="Upload a new user avatar", tags=["Users avatars"])
async def me_user_upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(IsAuthenicatedPermission()),
) -> UserResponseSchema:
    try:
        avatar_url = await upload_object_image(current_user, file)
    except ImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponseSchema(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        surname=current_user.surname,
        avatar_url=avatar_url,
    )


@router.get("/activity", tags=["Users statistics"])
async def me_user_get_activity(
    current_user: User = Depends(FamilyMemberPermission()),
) -> ActivitiesResponse | None:
    interval = DateRangeSchema(
        start=datetime.now() - timedelta(days=120),
        end=datetime.now(),
    )
    result = await get_user_activity(user_id=current_user.id, interval=interval)
    return result


# Get user's profile
@router.get("/profile/{user_id}", summary="Getting user's profile", tags=["Users"])
async def get_user_profile(
    user_id: UUID,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserProfileSchema:
    async with async_session.begin():
        try:
            user = await AsyncUserDAL(async_session).get_or_raise(user_id)
        except UserNotFoundError:
            raise HTTPException(
                status_code=404, detail={"detail": "User was not found"}
            )

    if user.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail={"detail": "User was not found"})

    result = UserProfileSchema(
        user=UserResponseSchema(
            id=user.id,
            username=user.username,
            name=user.name,
            surname=user.surname,
        ),
    )
    await update_user_avatars(result)
    return result
