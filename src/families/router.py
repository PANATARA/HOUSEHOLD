from datetime import datetime, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from core.exceptions.base_exceptions import ImageError
from core.exceptions.families import (
    FamilyNotFoundError,
    UserCannotLeaveFamily,
    UserIsAlreadyFamilyMember,
)
from core.exceptions.users import UserNotFoundError
from core.get_avatars import update_family_avatars, upload_object_image
from core.metrics_requests import (
    DateRangeSchema,
    get_family_members_ids_by_total_completions,
)
from core.permissions import (
    FamilyInvitePermission,
    FamilyMemberPermission,
    IsAuthenicatedPermission,
)
from core.security import create_jwt_token, get_payload_from_jwt_token
from database_connection import get_db
from families.repository import AsyncFamilyDAL, FamilyDataService
from families.schemas import (
    FamilyCreateSchema,
    FamilyDetailSchema,
    FamilyInviteSchema,
    FamilyResponseSchema,
    InviteTokenSchema,
)
from families.services import (
    AddUserToFamilyService,
    FamilyCreatorService,
    LogoutUserFromFamilyService,
)
from users.models import User
from users.repository import AsyncUserDAL
from users.schemas import UserFamilyPermissionModelSchema

logger = getLogger(__name__)

router = APIRouter()


# Create a new family
@router.post("", tags=["Family"])
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
            family_data_service = FamilyDataService(async_session)
            family_detail = await family_data_service.get_family_with_members(family.id)
            await update_family_avatars(family_detail)
            return family_detail


# Get user's family
@router.get(
    "", summary="Getting basic information about the user's family", tags=["Family"]
)
async def get_my_family(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyDetailSchema | None:
    async with async_session.begin():
        family_id = current_user.family_id

        family_data_service = FamilyDataService(async_session)
        family = await family_data_service.get_family_with_members(family_id)
        interval = DateRangeSchema(
            start=datetime.now() - timedelta(days=7),
            end=datetime.now(),
        )
        sorted_members = await get_family_members_ids_by_total_completions(
            family_id=family_id, interval=interval
        )
        await update_family_avatars(family)

        if sorted_members:
            family.sort_members_by_id(
                [sorted_members.user_id for sorted_members in sorted_members]
            )

        return family


# Logout user from family
@router.patch(path="/logout", summary="Logout me from family", tags=["Family members"])
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


@router.delete(path="/kick/{user_id}", summary="Kick user from family", tags=["Family members"])
async def kick_user_from_family(
    user_id: UUID,
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        try:
            user_repo = AsyncUserDAL(async_session)
            user = await user_repo.get_or_raise(user_id)
            if user.family_id != current_user.family_id:
                raise UserNotFoundError

            await LogoutUserFromFamilyService(
                user=user, db_session=async_session
            ).run_process()

        except UserNotFoundError as e:
            return JSONResponse(
                content={"message": str(e)},
                status_code=400,
            )

    return JSONResponse(
        content={"message": "OK"},
        status_code=200,
    )


# Change Family Administrator
@router.patch(path="/change_admin/{user_id}", tags=["Family members"])
async def change_family_admin(
    user_id: UUID,
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        family_dal = AsyncFamilyDAL(async_session)
        family_id = current_user.family_id
        if family_id is None:
            raise FamilyNotFoundError
        await family_dal.update(
            object_id=family_id, fields={"family_admin_id": user_id}
        )
    return JSONResponse(
        content={"detail": "New family administrator appointed"},
        status_code=status.HTTP_200_OK,
    )


@router.post(path="/invite", summary="Generate invite token", tags=["Family invited"])
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


# Join to family by invite-token
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
            family = await AsyncFamilyDAL(async_session).get_or_raise(family_id)
            service = AddUserToFamilyService(
                family=family,
                user=current_user,
                permissions=user_permissions,
                db_session=async_session,
            )
            await service.run_process()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The user is already a member of a family",
            )
        return JSONResponse(
            content={"message": "You have been successfully added to the family"},
            status_code=status.HTTP_200_OK,
        )


@router.post("/avatar/file/", summary="Upload new family's avatar", tags=["Family avatar"])
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyResponseSchema:
    async with async_session.begin():
        family = await AsyncFamilyDAL(async_session).get_by_id(current_user.family_id)

    try:
        family_avatar_url = await upload_object_image(family, file)
    except ImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FamilyResponseSchema(
        id=family.id, name=family.name, icon=family.icon, avatar_url=family_avatar_url
    )
