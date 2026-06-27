from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
from database_connection import get_db
from families.repository import FamilyRepository
from families.schemas import (
    FamilyCreateSchema,
    FamilyResponseSchema,
    FamilyMemberStatsSchema,
    FamilyMembersSchema,
    FamilyUpdateSchema,
    InviteTokenSchema,
)
from families.services import (
    FamilyCreatorService,
    GenerateFamilyInviteTokenService,
    JoinFamilyByInviteCodeService,
    LogoutUserFromFamilyService,
)
from statistics.repository import StatsRepository, get_statistic_repo
from users.models import User
from users.repository import UserRepository
from users.schemas import UserResponseSchema
from utils import get_current_week_range

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
) -> FamilyResponseSchema:
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
            return FamilyResponseSchema.model_validate(family)


@router.patch(
    path="/",
    summary="Update family's profile",
    tags=["Family"],
)
async def me_user_partial_update(
    body: FamilyUpdateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyResponseSchema:
    async with async_session.begin():
        repo = FamilyRepository(async_session)
        family = await repo.get_by_id(current_user.family_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(family, field, value)

        family = await repo.update(family)

    result_response = FamilyResponseSchema(
        id=family.id,
        name=family.name,
        icon=family.icon,
        icon_bg=family.icon_bg,
        icon_color=family.icon_color,
        experience=family.experience,
    )
    return result_response


@router.get(
    path="",
    summary="Get information about the user's family",
    tags=["Family"],
)
async def get_my_family(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyResponseSchema:
    async with async_session.begin():
        family_id = current_user.family_id
        family = await FamilyRepository(async_session).get_by_id(family_id)
    return FamilyResponseSchema.model_validate(family)


@router.get(
    path="/members",
    summary="",
    tags=["Family members"],
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
    path="/members/leader",
    summary="",
    tags=["Family members"],
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
        if len(members) == 0:
            return FamilyMemberStatsSchema(
                member=None,
                chore_completion_count=None,
            )
        user = await UserRepository(async_session).get_by_id(members[0].user_id)
        return FamilyMemberStatsSchema(
            member=UserResponseSchema.model_validate(user),
            chore_completion_count=members[0].chores_completions_counts,
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
    current_user: User = Depends(FamilyInvitePermission()),
    async_session: AsyncSession = Depends(get_db),
) -> InviteTokenSchema:
    async with async_session.begin():
        service = GenerateFamilyInviteTokenService(current_user, async_session)
        invite_code, ttl = await service.run_process()
    return InviteTokenSchema(
        invite_token=invite_code,
        ttl=ttl,
    )


@router.post(
    path="/join/{invite_code}",
    summary="Join to family by invite-token",
    tags=["Family invited"],
)
async def join_to_family(
    invite_code: str,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        service = JoinFamilyByInviteCodeService(
            user=current_user, invite_code=invite_code, db_session=async_session
        )
        await service.run_process()
        return JSONResponse(
            content={"message": "You have been successfully added to the family"},
            status_code=status.HTTP_200_OK,
        )


@router.post(
    path="/avatar/file/",
    summary="Upload new family's avatar",
    tags=["Family"],
    include_in_schema=False,
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
    tags=["Family"],
    response_model=None,
    include_in_schema=False,
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
