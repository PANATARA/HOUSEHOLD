from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import IsAuthenicatedPermission, IsFamilyAdminPermission
from db.session import get_db
from db.dals.families import AsyncFamilyDAL
from db.models.user import User
from schemas.families import FamilyCreate, FamilyFullShow, FamilyShow
from services.families.data import FamilyDataService
from services.families.services import FamilyCreatorService, LogoutUserFromFamilyService
from core.exceptions.families import FamilyNotFoundError, UserCannotLeaveFamily, UserIsAlreadyFamilyMember

from logging import getLogger

logger = getLogger(__name__)

families_router = APIRouter()


# Create a new family
@families_router.post("", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyShow:

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
            raise HTTPException(status_code=400, detail=  str(e))
        else:
            return FamilyShow(name=family.name)


# Get user's family
@families_router.get("", response_model=FamilyFullShow)
async def get_my_family(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> FamilyFullShow | None:

    async with async_session.begin():
        family_id = current_user.family_id
        if family_id is None:
            raise HTTPException(status_code=404, detail="Family not found")
        
        family_data_service = FamilyDataService(async_session)
        family = await family_data_service.get_family_with_users(family_id)

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
    current_user: User = Depends(IsFamilyAdminPermission()),
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
