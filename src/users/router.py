from datetime import datetime, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import StorageFolderEnum
from core.exceptions.base_exceptions import ImageError
from core.exceptions.users import UserError
from core.get_avatars import AvatarService, update_user_avatars, upload_object_image
from core.permissions import (
    FamilyMemberPermission,
    FamilyUserAccessPermission,
    IsAuthenicatedPermission,
)
from database_connection import get_db
from metrics import ActivitiesResponse, DateRangeSchema, get_user_activity
from users.aggregates import MeProfileSchema, UserProfileSchema
from users.models import User
from users.repository import AsyncUserDAL, UserDataService
from users.schemas import (
    UserCreateSchema,
    UserResponseSchema,
    UserSettingsResponseSchema,
    UserUpdateSchema,
)
from users.services import UserCreatorService
from wallets.repository import AsyncWalletDAL
from wallets.schemas import WalletBalanceSchema

logger = getLogger(__name__)


router = APIRouter()


def get_16_week_range_to_upcoming_sunday() -> DateRangeSchema:
    today = datetime.now()

    days_until_sunday = (6 - today.weekday()) % 7
    upcoming_sunday = (today + timedelta(days=days_until_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    start_sunday = upcoming_sunday - timedelta(weeks=16)

    return DateRangeSchema(start=start_sunday, end=upcoming_sunday)


@router.post(
    path="/me",
    tags=["Users"],
    summary="Create new user, user's settings",
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


@router.get(path="/me", summary="Get user's full profile information", tags=["Users"])
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
@router.patch(path="/me", summary="Update user information", tags=["Users"])
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


@router.get(path="/me/settings", summary="Get user's settings", tags=["Users settings"])
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsResponseSchema:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(user_id=current_user.id)


@router.post(
    path="me/avatar/file", summary="Upload a new user avatar", tags=["Users avatars"]
)
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


@router.get(
    path="/{user_id}/avatar/", summary="Get user's avatar", tags=["Users avatars"]
)
async def user_get_avatar(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
) -> UserResponseSchema:
    service = AvatarService(user_id, StorageFolderEnum.users_avatars)
    avatar_url = await service.run_process()
    return JSONResponse(content={"avatar_url": avatar_url}, status_code=200)


@router.get(
    path="/me/activity",
    summary="Get user's activity statistics",
    tags=["Users statistics"],
)
async def me_user_get_activity(
    current_user: User = Depends(FamilyMemberPermission()),
) -> ActivitiesResponse | None:
    interval = get_16_week_range_to_upcoming_sunday()
    result = await get_user_activity(user_id=current_user.id, interval=interval)
    return result


@router.get(
    path="/activity/{user_id}",
    summary="Get user's activity statistics",
    tags=["Users statistics"],
)
async def user_get_activity(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
) -> ActivitiesResponse | None:
    interval = get_16_week_range_to_upcoming_sunday()
    result = await get_user_activity(user_id=user_id, interval=interval)
    return result


@router.get(
    path="/{user_id}",
    summary="Get user's profile information by user ID",
    tags=["Users"],
)
async def get_user_profile(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserProfileSchema:
    async with async_session.begin():
        user = await AsyncUserDAL(async_session).get_by_id(user_id)

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
