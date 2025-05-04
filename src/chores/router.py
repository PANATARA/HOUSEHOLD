from datetime import datetime, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import AsyncChoreDAL, ChoreDataService
from chores.schemas import (
    ChoreCreateSchema,
    ChoreResponseSchema,
    ChoresListResponseSchema,
)
from chores.services import ChoreCreatorService
from core.permissions import (
    ChorePermission,
    FamilyMemberPermission,
)
from database_connection import get_db
from families.repository import AsyncFamilyDAL
from metrics import (
    DateRangeSchema,
    get_family_chores_ids_by_total_completions,
)
from users.models import User

logger = getLogger(__name__)

router = APIRouter()


@router.get(
    path="",
    summary="Get a list of chores for the user's family, optionally limited and sorted by completions in the last 7 days",
    tags=["Chore"],
)
async def get_family_chores(
    limit: int | None = Query(None, ge=1),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ChoresListResponseSchema | None:
    async with async_session.begin():
        family_chores = await ChoreDataService(async_session).get_family_chores(
            current_user.family_id, limit=limit
        )
        result_response = ChoresListResponseSchema(chores=family_chores)

        interval = DateRangeSchema(
            start=datetime.now() - timedelta(days=7),
            end=datetime.now(),
        )
        sorted_chores = await get_family_chores_ids_by_total_completions(
            current_user.family_id, interval=interval
        )
        if sorted_chores:
            result_response.sort_chores_by_id(
                [chore.chore_id for chore in sorted_chores]
            )
        return result_response


@router.post(
    path="",
    summary="Create a new chore for the user's family (admin only)",
    tags=["Chore"],
)
async def create_family_chore(
    body: ChoreCreateSchema,
    current_user: User = Depends(FamilyMemberPermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreResponseSchema:
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
        return ChoreResponseSchema(
            id=new_chore.id,
            name=new_chore.name,
            description=new_chore.description,
            icon=new_chore.icon,
            valuation=new_chore.valuation,
        )


@router.delete(
    path="/{chore_id}",
    summary="Delete a family chore by ID (admin only)",
    tags=["Chore"],
)
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
