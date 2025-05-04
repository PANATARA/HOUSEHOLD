from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import AsyncChoreDAL
from chores_completions.repository import ChoreCompletionDataService
from chores_completions.schemas import (
    ChoreCompletionCreateSchema,
    ChoreCompletionDetailSchema,
    ChoreCompletionResponseSchema,
)
from chores_completions.services import CreateChoreCompletion
from core.enums import StatusConfirmENUM
from core.exceptions.chores import ChoreNotFoundError
from core.get_avatars import update_user_avatars
from core.permissions import (
    ChoreCompletionPermission,
    ChorePermission,
    FamilyMemberPermission,
)
from core.query_depends import get_pagination_params
from database_connection import get_db
from users.models import User

logger = getLogger(__name__)

router = APIRouter()


@router.post(
    path="/{chore_id}",
    tags=["Chores completions"],
    summary="Create a chore completion for a specific chore",
    description="Marks a chore as completed by the current user. May require confirmation from other family members.",
)
async def create_chore_completion(
    chore_id: UUID,
    body: ChoreCompletionCreateSchema,
    current_user: User = Depends(ChorePermission(only_admin=False)),
    async_session: AsyncSession = Depends(get_db),
) -> Response:
    async with async_session.begin():
        try:
            chore = await AsyncChoreDAL(async_session).get_or_raise(chore_id)
            creator_service = CreateChoreCompletion(
                user=current_user,
                chore=chore,
                message=body.message,
                db_session=async_session,
            )
            await creator_service.run_process()
        except ChoreNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chore not found"
            )
    return JSONResponse(
        content={"detail": "Chore completion was created"},
        status_code=201,
    )


@router.get(
    path="",
    summary="Get a list of completed family chores sorted by date",
    tags=["Chores completions"],
)
async def get_family_chores_completions(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    status: StatusConfirmENUM | None = None,
    chore_id: UUID | None = Query(None),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ChoreCompletionResponseSchema]:
    async with async_session.begin():
        offset, limit = pagination
        data_service = ChoreCompletionDataService(async_session)
        result_response = await data_service.get_family_chore_completion(
            current_user.family_id, offset, limit, status, chore_id
        )
        await update_user_avatars(result_response)
        return result_response


# Get family's chore completion detail
@router.get(
    path="/{chore_completion_id}",
    summary="Retrieve detailed information about a specific chore completion",
    tags=["Chores completions"],
)
async def get_family_chore_completion_detail(
    chore_completion_id: UUID,
    current_user: User = Depends(ChoreCompletionPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreCompletionDetailSchema | None:
    async with async_session.begin():
        data_service = ChoreCompletionDataService(async_session)
        result_response = await data_service.get_family_chore_completion_detail(
            chore_completion_id
        )
        await update_user_avatars(result_response)
        return result_response
