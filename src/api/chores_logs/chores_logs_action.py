from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from services.chores_logs.services import CreateChoreLog
from schemas.chores_logs import ChoreLogCreate


from logging import getLogger

logger = getLogger(__name__)


async def _create_chore_log(
    body: ChoreLogCreate, user: User, async_session: AsyncSession
) -> Response:
    async with async_session.begin():
        creator_service = CreateChoreLog(
            user=user,
            chore_id=body.chore_id,
            message=body.message,
            db_session=async_session,
        )
        await creator_service()
        return Response(
            status_code=204,
        )

async def _confirm_chore_log(
    chorelog_id, body: ChoreLogCreate, user: User, async_session: AsyncSession
) -> Response:
    async with async_session.begin():
        return Response(
            status_code=204,
        )