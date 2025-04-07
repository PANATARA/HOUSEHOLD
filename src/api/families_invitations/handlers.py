from datetime import timedelta
from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from api.permissions import FamilyInvitePermission, IsAuthenicatedPermission
from core.qr_code import get_qr_code
from core.security import (
    create_jwt_token,
    get_payload_from_jwt_token,
)
from db.dals.families import AsyncFamilyDAL
from db.models.user import User
from db.session import get_db
from schemas.families import InviteToken, UserInviteParametr
from schemas.users import UserFamilyPermissionModel
from services.families.services import AddUserToFamilyService

logger = getLogger(__name__)

families_invitations_router = APIRouter()


# Generate invite token
@families_invitations_router.post(path="/invite", summary="Generate invite token")
async def generate_invite_token(
    body: UserInviteParametr,
    current_user: User = Depends(FamilyInvitePermission()),
) -> InviteToken:
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
        return InviteToken(
            invite_token=invite_token,
            life_time=timedelta(seconds=900),
        )


# Join to family by invite-token
@families_invitations_router.post(
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
        allowed_fields = UserFamilyPermissionModel.model_fields.keys()
        user_permissions = UserFamilyPermissionModel(
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
