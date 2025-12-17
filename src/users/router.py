from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import USE_S3_STORAGE
from core.exceptions.base_exceptions import ImageError
from core.get_avatars import (
    GetAvatarService,
    UploadAvatarService,
)
from core.permissions import (
    FamilyUserAccessPermission,
    IsAuthenicatedPermission,
)
from database_connection import get_db
from families.repository import FamilyRepository
from users.models import User
from users.repository import UserRepository, UserSettingsRepository
from users.schemas import (
    UserResponseSchema,
    UserResponseSchemaFull,
    UserSettingsResponseSchema,
    UserSettingsUpdateSchema,
    UserUpdateSchema,
    MeResponseSchemaFull,
)

logger = getLogger(__name__)


router = APIRouter()


@router.get(
    path="/me/profile",
    summary="Get current user's profile",
    tags=["Me"],
)
async def me_get_user_profile(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> MeResponseSchemaFull:
    is_family_member = current_user.family_id is not None
    is_family_admin = False

    if is_family_member:
        is_family_member = True
        async with async_session.begin():
            is_family_admin = await FamilyRepository(
                async_session
            ).user_is_family_admin(current_user.id, current_user.family_id)

    return MeResponseSchemaFull(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        surname=current_user.surname,
        avatar_version=current_user.avatar_version,
        experience=current_user.experience,
        is_family_member=is_family_member,
        is_family_admin=is_family_admin,
    )


@router.patch(
    path="/me/profile",
    summary="Update current user's profile",
    tags=["Me"],
)
async def me_user_partial_update(
    body: UserUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    async with async_session.begin():
        user_dal = UserRepository(async_session)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(current_user, field, value)

        user = await user_dal.update(current_user)

    result_response = UserResponseSchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
        avatar_version=user.avatar_version,
    )
    return result_response


@router.get(path="/me/settings", summary="Get current user's settings", tags=["Me"])
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsResponseSchema:
    async with async_session.begin():
        user_settings = await UserSettingsRepository(async_session).get_by_user_id(
            current_user.id
        )
        if user_settings is None:
            raise HTTPException(status_code=404)
        return UserSettingsResponseSchema(
            app_theme=user_settings.app_theme,
            language=user_settings.language,
            date_of_birth=user_settings.date_of_birth,
        )


@router.patch(
    path="/me/settings",
    summary="Update current user's settings",
    tags=["Me"],
)
async def me_user_settings_partial_update(
    body: UserSettingsUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsResponseSchema:
    async with async_session.begin():
        UserSettingsDal = UserSettingsRepository(async_session)
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


@router.get(
    path="/{user_id}",
    summary="Get user profile by ID",
    tags=["Users"],
)
async def get_user_profile(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseSchemaFull:
    async with async_session.begin():
        user = await UserRepository(async_session).get_by_id(user_id)
    result = UserResponseSchemaFull.model_validate(user)
    return result


@router.post(
    path="me/avatar/file",
    summary="Upload a new avatar for the current user",
    tags=["Me"],
)
async def me_user_upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        service = UploadAvatarService(
            target_object=current_user, file=file, db_session=async_session
        )
        try:
            new_avatar_url = await service.run_process()
        except ImageError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content={"avatar_url": new_avatar_url}, status_code=201)


@router.get(
    path="/{user_id}/avatar",
    summary="Get avatar for a user by ID",
    tags=["Users"],
    response_model=None,
)
async def user_get_avatar(
    user_id: UUID,
    avatar_version: str | None = Query(None, description="Avatar version"),
    current_user: User = Depends(FamilyUserAccessPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FileResponse | RedirectResponse:
    async with async_session.begin():
        service = GetAvatarService(
            target_kind="User", target_object_id=user_id, db_session=async_session
        )
        avatar = await service.run_process()

    if avatar is None:
        raise HTTPException(status_code=404, detail="User has no avatar")
    elif USE_S3_STORAGE:
        return RedirectResponse(url=avatar)
    else:
        return FileResponse(avatar)
