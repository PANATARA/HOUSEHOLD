from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession

from api.families.permissions import get_user_and_check_is_family_admin
from core.security import get_current_user_from_token
from db.session import get_db
from db.dals.families import AsyncFamilyDAL
from db.models.user import User
from schemas.families import FamilyCreate, FamilyFullShow, FamilyShow
from services.families.data import FamilyDataService
from services.families.services import FamilyCreatorService, LogoutUserFromFamilyService
from core.exceptions import UserCannotLeaveFamily, user_not_found

from logging import getLogger

logger = getLogger(__name__)

families_router = APIRouter()


# Create a new family
@families_router.post("", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate,
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyShow:

    async with async_session.begin():
        try:
            family_creator_service = FamilyCreatorService(
                name=body.name, user=current_user, db_session=async_session
            )
            family = family_creator_service()
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"detail": "The user is already a family member"},
            )
        except Exception as e:
            return JSONResponse(status_code=400, content={"detail": str(e)})
        else:
            return FamilyShow(name=family.name)


# Get user family
@families_router.get("", response_model=FamilyFullShow)
async def get_my_family(
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyFullShow:

    async with async_session.begin():
        data = await FamilyDataService(async_session).get_family_with_users(
            current_user.family_id
        )
        if data is None:
            raise HTTPException(status_code=404, detail=f"Family not found")

        return data


# Logout user from family
@families_router.patch(path="/logout", summary="Logout me from family")
async def logout_user_from_family(
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:

    async with async_session.begin():
        try:
            await LogoutUserFromFamilyService(
                user=current_user, db_session=async_session
            )()

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
    current_user: User = Depends(get_user_and_check_is_family_admin),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        family_dal = AsyncFamilyDAL(async_session)
        if await family_dal.user_is_family_member(user_id, current_user.family_id):
            await family_dal.update(
                object_id=current_user.family_id, fields={"family_admin_id": user_id}
            )
        else:
            raise user_not_found
    return JSONResponse(
        content={"detail": "New family administrator appointed"},
        status_code=status.HTTP_200_OK,
    )
