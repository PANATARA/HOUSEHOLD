from datetime import datetime, timedelta
from logging import getLogger

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.base_exceptions import ImageError
from core.exceptions.users import UserError
from core.metrics_requests import ActivitiesResponse, DateRangeSchema, get_user_activity
from core.permissions import IsAuthenicatedPermission, FamilyMemberPermission
from core.get_avatars import upload_object_image, update_user_avatars
from database_connection import get_db
from users.aggregates import UserProfileSchema
from users.models import User
from users.repository import AsyncUserDAL, UserDataService
from users.schemas import (
    UserCreateSchema,
    UserSettingsShowSchema,
    UserSummarySchema,
    UserUpdateSchema,
)
from users.services import UserCreatorService
from wallets.repository import AsyncWalletDAL
from wallets.schemas import WalletBalanceSchema


logger = getLogger(__name__)


user_router = APIRouter()


# Create new User
@user_router.post("")
async def create_user(
    body: UserCreateSchema, async_session: AsyncSession = Depends(get_db)
) -> UserSummarySchema:
    async with async_session.begin():
        try:
            service = UserCreatorService(
                user_data=body,
                db_session=async_session,
            )
            user = await service.run_process()
        except UserError as err:
            raise HTTPException(status_code=400, detail=f"Error: {err}")

    return UserSummarySchema(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )


# Get user's profile (all info)
@user_router.get("", summary="Getting basic information about a user")
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
        is_family_member=bool(current_user.family_id),
        wallet=WalletBalanceSchema(
            id=wallet.id,
            balance=wallet.balance,
        ) if wallet else None
    )
    await update_user_avatars(result)
    return result


# Update user
@user_router.patch("")
async def me_user_partial_update(
    body: UserUpdateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSummarySchema:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            object_id=current_user.id, fields=body.model_dump(exclude_unset=True)
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
@user_router.get("/settings", summary="Getting user settings")
async def me_user_get_settings(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UserSettingsShowSchema:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(user_id=current_user.id)


@user_router.post("/avatar/file", summary="Upload a new user avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(IsAuthenicatedPermission()),
) -> UserSummarySchema:
    
    try:
        avatar_url = await upload_object_image(current_user, file)
    except ImageError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    return UserSummarySchema(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        surname=current_user.surname,
        avatar_url=avatar_url,
    )

@user_router.get("/activity")
async def me_user_get_activity(
    current_user: User = Depends(FamilyMemberPermission()),
) -> ActivitiesResponse | None:
    
    interval = DateRangeSchema(
        start=datetime.now() - timedelta(days=120),
        end=datetime.now(),
    )
    result = await get_user_activity(user_id=current_user.id, interval=interval)
    return result
