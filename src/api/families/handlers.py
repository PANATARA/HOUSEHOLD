from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.families.permissions import get_user_and_check_is_family_admin
from db.models.user import User
from db.session import get_db
from schemas.families import (
    FamilyCreate,
    FamilyFullShow,
    FamilyShow,
    InviteToken,
    JoinFamily,
    UserInviteParametr,
)
from api.families.actions import (
    _change_family_admin,
    _create_family,
    _genarate_invite_token,
    _get_family,
    _join_to_family,
    _logout_user_from_family,
)

from logging import getLogger

logger = getLogger(__name__)

families_router = APIRouter()


# Create a new family
@families_router.post("", response_model=FamilyShow)
async def create_family(
    body: FamilyCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> FamilyShow:

    return await _create_family(current_user, body, db)


# Get user family
@families_router.get("", response_model=FamilyFullShow)
async def get_my_family(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> FamilyFullShow:

    return await _get_family(current_user, db)


# Logout user to family
@families_router.post(path="/logout", summary="Logout me from family")
async def logout_user_from_family(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    return await _logout_user_from_family(current_user, db)


# Kick user out of family
@families_router.post(
    path="/kick/user/{user_id}",
    summary="Kick user out of family.........NOT IMPLEMENTED",
)
async def kick_user_from_family(
    user_id: int,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:

    return


# Generate invite token
@families_router.post(path="/invite", summary="Generate invite token")
async def generate_invite_token(
    body: UserInviteParametr,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> InviteToken:
    return await _genarate_invite_token(body=body, user=current_user, async_session=db)


# Join to family by invite-token
@families_router.post(path="/join", summary="Join to family by invite-token")
async def join_to_family(
    body: JoinFamily,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return await _join_to_family(body=body, user=current_user, async_session=db)

# Change Family Administrator
@families_router.patch(path="/change_admin/{user_id}")
async def change_family_admin(
    user_id: UUID,
    current_user: User = Depends(get_user_and_check_is_family_admin),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return await _change_family_admin(
        new_admin_id=user_id,
        user=current_user,
        async_session=db
    )