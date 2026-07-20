from datetime import date, timedelta
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import ChoreRepository, DefaultChoreRepository
from chores.schemas import (
    ChoreCreateSchema,
    ChoreResponseSchema,
    ChoreUpdateSchema,
    ChoresFromDefaultsSchema,
    ChoresListResponseSchema,
    DefaultChoreResponseSchema,
)
from chores.services import (
    ChoreCreatorService,
    ChoreFromDefaultService,
    UpdateChoreService,
)
from core.permissions import (
    ChorePermission,
    FamilyMemberPermission,
)
from database_connection import get_db
from families.repository import FamilyRepository
from statistics.repository import StatsRepository, get_statistic_repo
from statistics.schemas import DateRangeSchema
from users.models import User
from users.repository import UserSettingsRepository

logger = getLogger(__name__)

router = APIRouter()


@router.get(
    path="",
    summary="Get a list of chores for the user's family, optionally limited",
    tags=["Chore"],
)
async def get_family_chores(
    limit: int | None = Query(None, ge=1),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
    stats_repo: StatsRepository = Depends(get_statistic_repo),
):
    family_chores = await ChoreRepository(async_session).get_family_chores(
        current_user.family_id,  # type: ignore
        limit=limit,
    )

    interval = DateRangeSchema(
        start=date.today() - timedelta(days=30),
        end=date.today(),
    )
    stats = await stats_repo.get_chores_by_completions(
        family_id=current_user.family_id,  # type: ignore
        interval=interval,
    )
    usage_map = {str(s.chore_id): s.chores_completions_counts for s in stats}

    family_chores.sort(key=lambda c: usage_map.get(str(c.id), 0), reverse=True)

    return ChoresListResponseSchema(chores=family_chores)


@router.post(
    path="",
    summary="Create a new chore for the user's family (admin only)",
    tags=["Chore"],
)
async def create_family_chore(
    body: ChoreCreateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreResponseSchema:
    async with async_session.begin():
        family = await FamilyRepository(async_session).get_by_id(current_user.family_id)
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
            icon_color=new_chore.icon_color,
            icon_bg=new_chore.icon_bg,
            valuation=new_chore.valuation,
            default_chore_id=new_chore.default_chore_id,
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
        chore_dal = ChoreRepository(async_session)
        result = await chore_dal.soft_delete(chore_id)

        if result:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail={"Chore was not found"}
            )


@router.patch(
    path="/{chore_id}",
    summary="Edit chore",
    tags=["Chore"],
)
async def edit_family_chore(
    chore_id: UUID,
    body: ChoreUpdateSchema,
    current_user: User = Depends(ChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreResponseSchema:
    async with async_session.begin():
        chore = await ChoreRepository(async_session).get_by_id(chore_id)
        service = UpdateChoreService(chore=chore, data=body, db_session=async_session)
        updated_chore = await service.run_process()

    return ChoreResponseSchema.model_validate(updated_chore)


@router.get(
    path="/default",
    summary="",
    tags=["Chores Default"],
)
async def get_default_chores(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[DefaultChoreResponseSchema]:
    async with async_session:
        default_chore_repo = DefaultChoreRepository(async_session)
        user_settings_repo = UserSettingsRepository(async_session)
        user_settings = await user_settings_repo.get_by_user_id(current_user.id)
        if user_settings is None:
            language = "en"
        else:
            language = user_settings.language
        result_response = await default_chore_repo.get_default_chores_not_added(
            current_user.family_id,  # type: ignore
            language,
        )

    return result_response


@router.post(
    path="/from-defaults",
    tags=["Chores Default"],
    response_model=ChoreResponseSchema | list[ChoreResponseSchema],
)
async def create_chores_from_defaults(
    body: ChoresFromDefaultsSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreResponseSchema | list[ChoreResponseSchema]:
    async with async_session.begin():
        service = ChoreFromDefaultService(
            family_id=current_user.family_id,  # type: ignore
            db_session=async_session,
            default_chore_ids=body.default_chore_ids,
            language=body.language,
        )
        chores = await service.run_process()

    if isinstance(chores, list):
        return [ChoreResponseSchema.model_validate(c) for c in chores]
    return ChoreResponseSchema.model_validate(chores)
