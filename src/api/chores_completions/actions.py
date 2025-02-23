from uuid import UUID
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from services.chores_completions.data import ChoreCompletionDataService
from services.chores_completions.services import CreateChoreCompletion
from schemas.chores_logs import ChoreCompletionCreate, ChoreCompletionDetailShow, ChoreCompletionShow


from logging import getLogger

logger = getLogger(__name__)


async def _create_chore_completion(
    body: ChoreCompletionCreate, user: User, async_session: AsyncSession
) -> Response:
    async with async_session.begin():
        creator_service = CreateChoreCompletion(
            user=user,
            chore_id=body.chore_id,
            message=body.message,
            db_session=async_session,
        )
        await creator_service()
        return Response(
            status_code=204,
        )

async def _get_family_chores_completions(
        page: int, limit: int, user: User, async_session: AsyncSession
) -> list[ChoreCompletionShow]:
    async with async_session.begin():
        offset = (page - 1) * limit
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion(user.family_id, offset, limit)
        return result

async def _get_family_chore_completion_detail(
        chore_completion_id: UUID, user: User, async_session: AsyncSession
) -> ChoreCompletionDetailShow:
    async with async_session.begin():
        data_service = ChoreCompletionDataService(async_session)
        result = await data_service.get_family_chore_completion_detail(chore_completion_id)
        return result