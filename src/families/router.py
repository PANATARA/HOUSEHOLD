from datetime import timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import USE_S3_STORAGE
from core.exceptions.base_exceptions import ImageError
from core.exceptions.families import (
    UserCannotLeaveFamily,
    UserIsAlreadyFamilyMember,
)
from core.get_avatars import (
    GetAvatarService,
    UploadAvatarService,
)
from core.permissions import (
    FamilyInvitePermission,
    FamilyMemberPermission,
    FamilyUserAccessPermission,
    IsAuthenicatedPermission,
)
from core.security import create_jwt_token, get_payload_from_jwt_token
from database_connection import get_db
from families.repository import FamilyRepository
from families.schemas import (
    FamilyCreateSchema,
    FamilyDetailSchema,
    FamilyInviteSchema,
    FamilyMemberStatsSchema,
    FamilyMembersSchema,
    FamilyResponseSchema,
    FamilyStatisticsSchema,
    InviteTokenSchema,
)
from families.services import (
    AddUserToFamilyService,
    FamilyCreatorService,
    LogoutUserFromFamilyService,
)
from statistics.repository import StatsRepository, get_statistic_repo
from statistics.schemas import UserChoresCountSchema
from users.models import User
from users.repository import UserRepository
from users.schemas import UserFamilyPermissionModelSchema, UserResponseSchema
from utils import get_current_month_range, get_current_week_range

logger = getLogger(__name__)

router = APIRouter()


@router.post(
    path="",
    summary="Create a new family and add the current user as a member",
    tags=["Family"],
)
async def create_family(
    body: FamilyCreateSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyDetailSchema | None:
    async with async_session.begin():
        try:
            family_creator_service = FamilyCreatorService(
                name=body.name, user=current_user, db_session=async_session
            )
            family = await family_creator_service.run_process()
        except UserIsAlreadyFamilyMember:
            raise HTTPException(
                status_code=400,
                detail="The user is already a family member",
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        else:
            family_data_service = FamilyRepository(async_session)
            family_detail = await family_data_service.get_family_members(family.id)
            return family_detail


@router.get(
    path="",
    summary="Get information about the user's family",
    tags=["Family"],
)
async def get_my_family(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
) -> FamilyDetailSchema:
    async with async_session.begin():
        family_id = current_user.family_id
        family = await FamilyRepository(async_session).get_by_id(family_id)
        weekly_stats = await statsRepo.get_family_chore_completion_count(
            family_id=family_id, interval=get_current_week_range()
        )
        monthly_stats = await statsRepo.get_family_chore_completion_count(
            family_id=family_id, interval=get_current_month_range()
        )
    return FamilyDetailSchema(
        family=FamilyResponseSchema.model_validate(family),
        statistics=FamilyStatisticsSchema(
            weekly_completed_chores=weekly_stats, monthly_completed_chores=monthly_stats
        ),
    )


@router.get(
    path="/members",
    summary="",
    tags=["Family"],
)
async def get_family_members(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyMembersSchema:
    async with async_session.begin():
        family_id: UUID = current_user.family_id  # type: ignore
        family_repo = FamilyRepository(async_session)
        family_members = await family_repo.get_family_members(family_id)
        return FamilyMembersSchema(members=family_members)


@router.get(
    path="/members",
    summary="",
    tags=["Family"],
)
async def get_family_leader(
    current_user: User = Depends(FamilyMemberPermission()),
    statsRepo: StatsRepository = Depends(get_statistic_repo),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyMemberStatsSchema:
    async with async_session.begin():
        family_id: UUID = current_user.family_id  # type: ignore
        members = await statsRepo.get_family_members_by_chores_completions(
            family_id, interval=get_current_week_range()
        )
        leader = members[0]
        user = await UserRepository(async_session).get_by_id(leader.user_id)
        return FamilyMemberStatsSchema(
            member=UserResponseSchema.model_validate(user),
            chore_completion_count=leader.chores_completions_counts,
        )


@router.patch(
    path="/logout",
    summary="Logout the user from the family, preventing administrators from leaving",
    tags=["Family members"],
)
async def logout_user_from_family(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        try:
            await LogoutUserFromFamilyService(
                user=current_user, db_session=async_session
            ).run_process()

        except UserCannotLeaveFamily:
            return JSONResponse(
                content={
                    "message": "You cannot leave a family while you are its administrator."
                },
                status_code=400,
            )

    return JSONResponse(
        content={"message": "OK"},
        status_code=200,
    )


@router.delete(
    path="/kick/{user_id}",
    summary="Kick a user from the family (admin only)",
    tags=["Family members"],
)
async def kick_user_from_family(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        user = await UserRepository(async_session).get_by_id(user_id)
        await LogoutUserFromFamilyService(
            user=user, db_session=async_session
        ).run_process()

    return JSONResponse(
        content={"message": "OK"},
        status_code=200,
    )


@router.patch(
    path="/change_admin/{user_id}",
    summary="Change the family administrator",
    tags=["Family members"],
)
async def change_family_admin(
    user_id: UUID,
    current_user: User = Depends(FamilyUserAccessPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        family_dal = FamilyRepository(async_session)
        family = await family_dal.get_by_id(current_user.family_id)
        family.family_admin_id = user_id
        await family_dal.update(family)
    return JSONResponse(
        content={"detail": "New family administrator appointed"},
        status_code=status.HTTP_200_OK,
    )


@router.post(
    path="/invite",
    summary="Generate an invite token for family invitations",
    tags=["Family invited"],
)
async def generate_invite_token(
    body: FamilyInviteSchema,
    current_user: User = Depends(FamilyInvitePermission()),
) -> InviteTokenSchema:
    payload = body.model_dump()
    payload["family_id"] = str(current_user.family_id)
    invite_token = create_jwt_token(data=payload, expires_delta=timedelta(seconds=900))
    return InviteTokenSchema(
        invite_token=invite_token,
        life_time=timedelta(seconds=900),
    )


@router.post(
    path="/join/{invite_token}",
    summary="Join to family by invite-token",
    tags=["Family invited"],
)
async def join_to_family(
    invite_token: str,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        payload = get_payload_from_jwt_token(invite_token)
        family_id = payload.get("family_id")
        allowed_fields = UserFamilyPermissionModelSchema.model_fields.keys()
        user_permissions = UserFamilyPermissionModelSchema(
            **{key: payload[key] for key in allowed_fields if key in payload}
        )
        try:
            family = await FamilyRepository(async_session).get_by_id(family_id)
            service = AddUserToFamilyService(
                family=family,
                user=current_user,
                permissions=user_permissions,
                db_session=async_session,
            )
            await service.run_process()
        except UserIsAlreadyFamilyMember:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The user is already a member of a family",
            )
        return JSONResponse(
            content={"message": "You have been successfully added to the family"},
            status_code=status.HTTP_200_OK,
        )


@router.post(
    path="/avatar/file/", summary="Upload new family's avatar", tags=["Family avatar"]
)
async def upload_family_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        family = await FamilyRepository(async_session).get_by_id(current_user.family_id)
        service = UploadAvatarService(
            target_object=family, file=file, db_session=async_session
        )
        try:
            new_avatar_url = await service.run_process()
        except ImageError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse({"avatar_url": new_avatar_url})


@router.get(
    path="/avatar",
    summary="Get family's avatar",
    tags=["Family avatar"],
    response_model=None,
)
async def family_get_avatar(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FileResponse | RedirectResponse:
    async with async_session.begin():
        service = GetAvatarService(
            target_kind="Family",
            target_object_id=current_user.family_id,
            db_session=async_session,
        )
        avatar = await service.run_process()

    if avatar is None:
        raise HTTPException(status_code=404, detail="no avatar")
    elif USE_S3_STORAGE:
        return RedirectResponse(url=avatar)
    else:
        return FileResponse(avatar)
