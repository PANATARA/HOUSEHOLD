from datetime import date
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import ChoreRepository
from core.permissions import (
    ChorePermission,
    FamilyMemberPermission,
    PlannedChorePermission,
)
from database_connection import get_db
from planned_chores.repository import ChoreScheduleRepository, PlannedChoreRepository
from planned_chores.schemas import (
    ChoreScheduleResponseSchema,
    CreateChoreScheduleSchema,
    PlannedChoreCreateSchema,
    PlannedChoreResponseSchema,
)
from planned_chores.services import (
    CompletePlannedChore,
    CreateChoreScheduleService,
    CreatePlannedChore,
    DeletePlannedChore,
    UncompletePlannedChore,
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
        planned_chore = await service.run_process()
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
        await service.run_process()

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
) -> PlannedChoreResponseSchema:
    async with async_session.begin():
        repo = PlannedChoreRepository(async_session)
        planned_chore = await repo.get_by_id(planned_chore_id)
        service = CompletePlannedChore(
            planned_chore=planned_chore,
            completed_by=current_user,
            db_session=async_session,
        )
        await service.run_process()
        planned_chore_full = await repo.get_planned_chore_by_id(planned_chore.id)
        return PlannedChoreResponseSchema.model_validate(planned_chore_full)


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
    async with async_session.begin():
        repo = PlannedChoreRepository(async_session)
        planned_chore = await repo.get_by_id(planned_chore_id)
        service = UncompletePlannedChore(
            planned_chore=planned_chore,
            db_session=async_session,
        )
        await service.run_process()
        planned_chore_full = await repo.get_planned_chore_by_id(planned_chore.id)
        return PlannedChoreResponseSchema.model_validate(planned_chore_full)


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
    due_date: date | None = Query(default=None),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[PlannedChoreResponseSchema]:
    repo = PlannedChoreRepository(async_session)
    result = await repo.get_family_planned_chores(
        family_id=current_user.family_id,  # type: ignore
        date_from=due_date,
        date_to=due_date,
    )

    return result


@router.post(
    path="/{chore_id}/schedules",
    tags=["Chore Schedule"],
    response_model=ChoreScheduleResponseSchema,
)
async def create_chore_schedule(
    chore_id: UUID,
    body: CreateChoreScheduleSchema,
    current_user: User = Depends(ChorePermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreScheduleResponseSchema:
    async with async_session.begin():
        chore = await ChoreRepository(async_session).get_by_id(chore_id)
        if chore is None:
            raise HTTPException(status_code=404, detail="Chore not found")

        assigned_to = await UserRepository(async_session).get_by_id(body.assigned_to_id)
        if assigned_to is None:
            raise HTTPException(status_code=404, detail="User not found")

        service = CreateChoreScheduleService(
            chore=chore,
            assigned_to=assigned_to,
            created_by=current_user,
            frequency_type=body.frequency_type,
            interval=body.interval,
            days_of_week=body.days_of_week,
            day_of_month=body.day_of_month,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            db_session=async_session,
        )
        schedule = await service.run_process()

    return ChoreScheduleResponseSchema.model_validate(schedule)


@router.delete(
    path="/{chore_id}/schedules/{schedule_id}",
    tags=["Chore Schedule"],
    status_code=204,
)
async def delete_chore_schedule(
    chore_id: UUID,
    schedule_id: UUID,
    current_user: User = Depends(ChorePermission(only_admin=True)),
    async_session: AsyncSession = Depends(get_db),
) -> None:
    async with async_session.begin():
        schedule = await ChoreScheduleRepository(async_session).get_by_id(schedule_id)

        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if schedule.chore_id != chore_id:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if schedule.family_id != current_user.family_id:
            raise HTTPException(status_code=403, detail="Access denied")

        await ChoreScheduleRepository(async_session).hard_delete(schedule_id)
