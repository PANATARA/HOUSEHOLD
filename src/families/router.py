from datetime import date, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from analytics.click_house_connection import get_click_house_client
from analytics.repository import ChoreAnalyticRepository
from analytics.schemas import DateRange
from core.exceptions.base_exceptions import ImageError
from core.permissions import FamilyInvitePermission, FamilyMemberPermission, IsAuthenicatedPermission
from core.exceptions.families import (
    FamilyNotFoundError,
    UserCannotLeaveFamily,
    UserIsAlreadyFamilyMember,
)
from core.get_avatars import update_family_avatars, upload_object_image
from core.qr_code import get_qr_code
from core.security import create_jwt_token, get_payload_from_jwt_token
from core.session import get_db
from core.storage import PresignedUrl
from families.repository import AsyncFamilyDAL, FamilyDataService
from families.schemas import FamilyCreateSchema, FamilyDetailSchema, InviteTokenSchema, FamilyInviteSchema
from families.services import AddUserToFamilyService, FamilyCreatorService, LogoutUserFromFamilyService
from users.models import User
from users.schemas import UserFamilyPermissionModelSchema


logger = getLogger(__name__)

families_router = APIRouter()


# Create a new family
@families_router.post("", response_model=FamilyDetailSchema)
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
@families_router.get("", response_model=FamilyDetailSchema)
async def get_my_family(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyDetailSchema | None:

    async with async_session.begin():
        family_id = current_user.family_id

        family_data_service = FamilyDataService(async_session)
        date_end = date.today()
        date_start = date_end - timedelta(days=7)
        family = await family_data_service.get_family_with_members(
            family_id
        )
        async_click_house_client = await get_click_house_client()
        analytic_repo = ChoreAnalyticRepository(async_click_house_client)

        top_user = await analytic_repo.get_member_by_completions_counts(
            family_id, DateRange(date_start=date_start, date_end=date_end)
        )
        total_chore_completions = await analytic_repo.get_family_chore_completion_count(
            family_id, DateRange(date_start=date_start, date_end=date_end)
        )
        family.top_member_weekly = top_user
        family.total_completed_chores = total_chore_completions
        await update_family_avatars(family)
        return family


# Logout user from family
@families_router.patch(path="/logout", summary="Logout me from family")
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


# Change Family Administrator
@families_router.patch(path="/change_admin/{user_id}")
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


@families_router.post(path="/invite", summary="Generate invite token", response_class=StreamingResponse)
async def generate_invite_token(
    body: FamilyInviteSchema,
    current_user: User = Depends(FamilyInvitePermission()),
) -> StreamingResponse:
    payload = body.model_dump()
    payload["family_id"] = str(current_user.family_id)
    invite_token = create_jwt_token(
        data=payload, expires_delta=timedelta(seconds=900)
    )
    qrcode = await get_qr_code(invite_token, 300)
    if qrcode:
        return StreamingResponse(
            qrcode, media_type="image/png", status_code=status.HTTP_201_CREATED
        )
    else:
        return InviteTokenSchema(
            invite_token=invite_token,
            life_time=timedelta(seconds=900),
        )


# Join to family by invite-token
@families_router.post(
    path="/join/{invite_token}", summary="Join to family by invite-token"
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

@families_router.post("/avatar/file/", summary="Upload new family's avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> PresignedUrl:
    
    async with async_session.begin():
        family = await AsyncFamilyDAL(async_session).get_by_id(current_user.family_id)
    
    try:
        family_avatar_url = await upload_object_image(family, file)
    except ImageError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    return family_avatar_url