from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.permissions import (
    FamilyUserAccessPermission,
    IsAuthenicatedPermission,
)
from database_connection import get_db
from families.repository import FamilyRepository
from src.statistics.repository import StatsRepository, get_statistic_repo
from src.utils import get_current_month_range, get_current_week_range
from users.models import User
from users.repository import UserRepository, UserSettingsRepository
from users.schemas import (
    UserResponseProfile,
    UserResponseSchema,
    UserSettingsResponseSchema,
    UserSettingsUpdateSchema,
    UserUpdateSchema,
)
from users.services import get_level_info

logger = getLogger(__name__)


router = APIRouter()


@router.get(
    path="/me/profile",
    summary="Get current user's profile",
    tags=["Me"],
)
async def me_get_user_profile(
    current_user: User = Depends(IsAuthenicatedPermission()),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseProfile:
    is_family_member = current_user.family_id is not None
    is_family_admin = False

    if is_family_member:
        is_family_member = True
        async with async_session.begin():
            is_family_admin = await FamilyRepository(
                async_session
            ).user_is_family_admin(current_user.id, current_user.family_id)

    level_info = get_level_info(current_user.experience)
    week_completed = await statsRepo.get_users_chore_completion_count(
        [current_user.id],
        interval=get_current_week_range(),
    )
    month_completed = await statsRepo.get_users_chore_completion_count(
        [current_user.id],
        interval=get_current_month_range(),
    )
    return UserResponseProfile.model_validate(
        {
            **current_user.__dict__,
            **level_info,
            "week_completed": week_completed[0].chores_completions_counts,
            "month_completed": month_completed[0].chores_completions_counts,
            "is_family_member": is_family_member,
            "is_family_admin": is_family_admin,
        }
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
        icon=user.icon,
        icon_bg=user.icon_bg,
        icon_color=user.icon_color,
        experience=user.experience,
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
    statsRepo: StatsRepository = Depends(get_statistic_repo),
    async_session: AsyncSession = Depends(get_db),
) -> UserResponseProfile:
    async with async_session.begin():
        user = await UserRepository(async_session).get_by_id(user_id)
        is_family_admin = await FamilyRepository(async_session).user_is_family_admin(
            user_id,
            current_user.family_id,  # type: ignore
        )

    level_info = get_level_info(user.experience)
    week_completed = await statsRepo.get_users_chore_completion_count(
        [user_id],
        interval=get_current_week_range(),
    )
    month_completed = await statsRepo.get_users_chore_completion_count(
        [current_user.id],
        interval=get_current_month_range(),
    )

    return UserResponseProfile.model_validate(
        {
            **user.__dict__,
            **level_info,
            "week_completed": week_completed[0].chores_completions_counts,
            "month_completed": month_completed[0].chores_completions_counts,
            "is_family_member": True,
            "is_family_admin": is_family_admin,
        }
    )
