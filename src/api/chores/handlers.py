from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import (
    ChorePermission,
    FamilyMemberPermission,
)
from db.dals.chores import AsyncChoreDAL
from db.dals.families import AsyncFamilyDAL
from db.models.user import User
from db.session import get_db
from schemas.chores.chores import NewChoreCreate, NewChoreDetail, NewChoreSummary
from schemas.chores.compositions import NewChoreDetailMax
from services.chores.data import ChoreDataService
from services.chores.services import ChoreCreatorService

logger = getLogger(__name__)

chores_router = APIRouter()


# List of all family  chores
@chores_router.get("")
async def get_family_chores(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[NewChoreSummary] | None:
    async with async_session.begin():
        return await ChoreDataService(async_session).get_family_chores(
            current_user.family_id
        )


# Get chore and related objects
@chores_router.get(path="/{chore_id}")
async def get_family_chore_detail(
    chore_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=30),
    current_user: User = Depends(ChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
) -> NewChoreDetailMax:
    offset = (page - 1) * limit
    async with async_session.begin():

        chore_data_service = ChoreDataService(async_session)
        data = await chore_data_service.get_family_chore_with_chore_completions(
            chore_id=chore_id, limit=limit, offset=offset
        )
        return data


# Create a new family chore
@chores_router.post("", response_model=NewChoreDetail)
async def create_family_chore(
    body: NewChoreCreate,
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> NewChoreDetail:
    async with async_session.begin():
        family = await AsyncFamilyDAL(async_session).get_or_raise(
            current_user.family_id
        )
        creator_service = ChoreCreatorService(
            family=family,
            db_session=async_session,
            data=body,
        )
        new_chore = await creator_service.run_process()
        return NewChoreDetail(
            id=new_chore.id,
            name=new_chore.name,
            description=new_chore.description,
            icon=new_chore.icon,
            valuation=new_chore.valuation,
            created_at=new_chore.created_at,
        )


@chores_router.delete(path="/{chore_id}")
async def delete_family_chore(
    chore_id: UUID,
    current_user: User = Depends(ChorePermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> Response:
    async with async_session.begin():
        chore_dal = AsyncChoreDAL(async_session)
        result = await chore_dal.soft_delete(chore_id)

        if result:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail={"Chore was not found"}
            )
