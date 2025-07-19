from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import StorageFolderEnum
from core.exceptions.base_exceptions import ImageError
from core.get_avatars import AvatarService, update_user_avatars, upload_object_image
from core.permissions import (
    FamilyUserAccessPermission,
    IsAuthenicatedPermission,
)
from database_connection import get_db
from users.aggregates import MeProfileSchema, UserProfileSchema
from users.models import User
from users.repository import AsyncUserDAL, AsyncUserSettingsDAL, UserDataService
from users.schemas import (
    UserResponseSchema,
    UserSettingsResponseSchema,
    UserSettingsUpdateSchema,
    UserUpdateSchema,
)
from wallets.repository import AsyncWalletDAL
from wallets.schemas import WalletBalanceSchema

logger = getLogger(__name__)


router = APIRouter()


@router.get(
    path="/me/profile",
    summary="Get user's full profile information",
    tags=["Users Profile"],
)
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
        is_profile_complete=bool(current_user.username) and bool(current_user.surname),
        wallet=wallet_response,
    )

    return result_response


@router.patch(
    path="/me/profile",
    summary="Update user's profile information",
    tags=["Users Profile"],
)
async def me_user_partial_update(
    body: UserUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(current_user, field, value)

        user = await user_dal.update(current_user)

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


@router.patch(
    path="/me/settings",
    summary="Update user's settings",
    tags=["Users settings"],
)
async def me_user_settings_partial_update(
    body: UserSettingsUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsResponseSchema:
    async with async_session.begin():
        UserSettingsDal = AsyncUserSettingsDAL(async_session)
        user_settings = await UserSettingsDal.get_by_user_id(current_user.id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(user_settings, field, value)

        user_settings = await UserSettingsDal.update(user_settings)

    result_response = UserSettingsResponseSchema(
        app_theme=user_settings.app_theme,
        language=user_settings.language,
        date_of_birth=user_settings.date_of_birth,
    )
    return result_response


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
    path="/{user_id}/avatar", summary="Get user's avatar", tags=["Users avatars"]
)
async def user_get_avatar(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
) -> JSONResponse:
    service = AvatarService(user_id, StorageFolderEnum.users_avatars)
    avatar_url = await service.run_process()
    return JSONResponse(content={"avatar_url": avatar_url}, status_code=200)


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
