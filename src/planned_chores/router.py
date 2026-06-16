from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import ChoreRepository
from core.permissions import (
    ChorePermission,
    FamilyMemberPermission,
    PlannedChorePermission,
)
from database_connection import get_db
from planned_chores.repository import PlannedChoreRepository
from planned_chores.schemas import PlannedChoreCreateSchema
from planned_chores.services import (
    CompletePlannedChore,
    CreatePlannedChore,
    DeletePlannedChore,
)
from users.models import User
from users.repository import UserRepository

logger = getLogger(__name__)

router = APIRouter()


@router.post(
    path="/{chore_id}/planned",
    tags=["Planned Chore"],
    summary="Create a Planned chore",
    description="...",
)
async def create_planned_chore(
    chore_id: UUID,
    body: PlannedChoreCreateSchema,
    current_user: User = Depends(ChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        chore = await ChoreRepository(async_session).get_by_id(chore_id)

        assigned_to_user = None
        if body.assigned_to_id is not None:
            assigned_to_user = await UserRepository(async_session).get_by_id(
                body.assigned_to_id
            )

        service = CreatePlannedChore(
            schedule=None,
            chore=chore,
            assigned_to_user=assigned_to_user,
            created_by=current_user,
            due_date=body.due_date,
            message=body.message,
            db_session=async_session,
        )
        planned_chore = await service.process()
        return JSONResponse(
            content={"id": str(planned_chore.id)}, status_code=status.HTTP_201_CREATED
        )


@router.delete(
    path="/planned/{planned_chore_id}",
    tags=["Planned Chore"],
    summary="Delete a Planned chore",
    description="...",
)
async def delete_planned_chore(
    planned_chore_id: UUID,
    current_user: User = Depends(PlannedChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
) -> Response:
    async with async_session.begin():
        planned_chore = await PlannedChoreRepository(async_session).get_by_id(
            planned_chore_id
        )
        service = DeletePlannedChore(
            planned_chore=planned_chore,
            db_session=async_session,
        )
        await service.process()

        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    path="/planned/{planned_chore_id}/complete",
    tags=["Planned Chore"],
    summary="Complete a Planned chore",
    description="...",
)
async def complete_planned_chore(
    planned_chore_id: UUID,
    current_user: User = Depends(PlannedChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        planned_chore = await PlannedChoreRepository(async_session).get_by_id(
            planned_chore_id
        )
        service = CompletePlannedChore(
            planned_chore=planned_chore,
            completed_by=current_user,
            db_session=async_session,
        )
        planned_chore = await service.process()
        return JSONResponse(
            content={"id": str(planned_chore.id)}, status_code=status.HTTP_202_ACCEPTED
        )


@router.patch(
    path="/planned/{planned_chore_id}/uncomplete",
    tags=["Planned Chore"],
    summary="Uncomplete a Planned chore",
    description="...",
)
async def uncomplete_planned_chore(
    planned_chore_id: UUID,
    current_user: User = Depends(PlannedChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
):
    pass


@router.patch(
    path="/planned/{planned_chore_id}/reschedule",
    tags=["Planned Chore"],
    summary="Reschedule a Planned chore",
    description="...",
)
async def reschedule_planned_chore(
    planned_chore_id: UUID,
    current_user: User = Depends(PlannedChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
):
    pass


@router.get(
    path="/planned",
    summary="Get planed_chores",
    tags=["Planned Chore"],
)
async def get_family_planned_chore(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    pass
