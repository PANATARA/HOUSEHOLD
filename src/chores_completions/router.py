from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import AsyncChoreDAL
from chores_completions.repository import ChoreCompletionDataService
from chores_completions.schemas import (
    ChoreCompletionCreateSchema,
    ChoreCompletionDetailSchema,
    ChoreCompletionSchema,
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
from database_connection import get_db
from users.models import User

logger = getLogger(__name__)

chores_completions_router = APIRouter()


# Create a new chore completion
@chores_completions_router.post(path="/{chore_id}")
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
    return Response(
        status_code=204,
    )


# Get family's chores completions
@chores_completions_router.get("", summary="Get a list of completed family chores sorted by date")
async def get_family_chores_completions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=50),
    status: StatusConfirmENUM | None = None,
    chore_id: UUID | None = Query(None),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ChoreCompletionSchema]:

    async with async_session.begin():
        offset = (page - 1) * limit
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion(
            current_user.family_id, offset, limit, status, chore_id
        )
        await update_user_avatars(result)
        return result


# Get family's chore completion detail
@chores_completions_router.get("/{chore_completion_id}", summary="Get chore execution details")
async def get_family_chore_completion_detail(
    chore_completion_id: UUID,
    current_user: User = Depends(ChoreCompletionPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ChoreCompletionDetailSchema | None:

    async with async_session.begin():
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion_detail(
            chore_completion_id
        )
        await update_user_avatars(result)
        return result
