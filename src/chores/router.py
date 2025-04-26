# from datetime import date, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import AsyncChoreDAL, ChoreDataService
from chores.services import ChoreCreatorService
from core.permissions import (
    ChorePermission,
    FamilyMemberPermission,
)
from database_connection import get_db
from chores.schemas import ChoreCreateSchema, ChoreSchema
from families.repository import AsyncFamilyDAL
from users.models import User

logger = getLogger(__name__)

chores_router = APIRouter()


# List of all family  chores
@chores_router.get("", summary="List of all families chore , sorted by number of completed")
async def get_family_chores(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ChoreSchema] | None:
    async with async_session.begin():
        family_chores = await ChoreDataService(async_session).get_family_chores(
            current_user.family_id
        )
        return family_chores


# Create a new family chore
@chores_router.post("")
async def create_family_chore(
    body: ChoreCreateSchema,
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreSchema:
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
        return ChoreSchema(
            id=new_chore.id,
            name=new_chore.name,
            description=new_chore.description,
            icon=new_chore.icon,
            valuation=new_chore.valuation,
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
