from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jose import ExpiredSignatureError, jwt
from jose import JWTError
from starlette import status

from config import auth_token
from core.exceptions import UserCannotLeaveFamily, user_not_found
from core.qr_code import get_qr_code
from core.security import create_access_token
from db.dals.families import AsyncFamilyDAL
from schemas.families import FamilyShow, InviteToken, JoinFamily, UserInviteParametr
from schemas.users import UserCreate, UserFamilyPermissionModel
from db.models.user import User
from services.families.data import FamilyDataService
from services.families.services import (
    AddUserToFamilyService,
    FamilyCreatorService,
    LogoutUserFromFamilyService,
)


from logging import getLogger

logger = getLogger(__name__)

user_router = APIRouter()


async def _create_family(
    user: User, body: UserCreate, async_session: AsyncSession
) -> FamilyShow:

    try:
        async with async_session.begin():
            family = await FamilyCreatorService(
                name=body.name, user=user, db_session=async_session
            )()
            return FamilyShow(name=family.name)
    except ValueError as e:
        return JSONResponse(
            status_code=400, content={"detail": "The user is already a family member"}
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


async def _get_family(
    user: User, async_session: AsyncSession
) -> FamilyShow | HTTPException:
    async with async_session.begin():
        data = await FamilyDataService(async_session).get_family_with_users(
            user.family_id
        )
        if data is None:
            raise HTTPException(status_code=404, detail=f"Family not found")

        return data

async def _logout_user_from_family(
    user: User, async_session: AsyncSession
) -> JSONResponse:
    async with async_session.begin():
        try:
            await LogoutUserFromFamilyService(user=user, db_session=async_session)()

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


async def _genarate_invite_token(
    body: UserInviteParametr, user: User, async_session: AsyncSession
) -> InviteToken:
    payload = body.model_dump()
    payload["family_id"] = str(user.family_id)
    invite_token = create_access_token(
        data=payload, expires_delta=timedelta(seconds=900)
    )
    qrcode = await get_qr_code(invite_token, 300)
    if qrcode:
        return StreamingResponse(qrcode, media_type="image/png")
    else:
        return InviteToken(
            invite_token=invite_token,
            life_time=timedelta(seconds=900),
        )
    


async def _join_to_family(
    body: JoinFamily, user: User, async_session: AsyncSession
) -> JSONResponse:
    async with async_session.begin():
        token = body.invite_token

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        try:
            payload = jwt.decode(
                token, auth_token.SECRET_KEY, algorithms=[auth_token.ALGORITHM]
            )
            family_id = payload.get("family_id")
            allowed_fields = UserFamilyPermissionModel.model_fields.keys()
            user_permissions = UserFamilyPermissionModel(
                **{key: payload[key] for key in allowed_fields if key in payload}
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invite token has expired",
            )
        except JWTError:
            raise credentials_exception

        family = await AsyncFamilyDAL(async_session).get_by_id(family_id)
        service = AddUserToFamilyService(
            family=family,
            user=user,
            permissions=user_permissions,
            db_session=async_session,
        )
        try:
            await service()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The user is already a member of a family",
            )

        return JSONResponse(
            content={"message": "You have been successfully added to the family"},
            status_code=status.HTTP_200_OK
        )

async def _change_family_admin(
    new_admin_id: UUID, user: User,async_session: AsyncSession
) -> JSONResponse:
    async with async_session.begin():
        family_dal = AsyncFamilyDAL(async_session)
        if await family_dal.user_is_family_member(new_admin_id, user.family_id):
            await family_dal.update(
                object_id=user.family_id,
                fields={"family_admin_id": new_admin_id}
            )
        else:
            raise user_not_found
    return JSONResponse(
        content={"detail": "New family administrator appointed"},
        status_code=status.HTTP_200_OK
    )
