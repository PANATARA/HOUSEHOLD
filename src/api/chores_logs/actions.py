from uuid import UUID
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from services.chores_logs.data import ChoreLogDataService
from services.chores_logs.services import CreateChoreLog
from schemas.chores_logs import ChoreLogCreate, ChoreLogDetailShow, ChoreLogShow


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

async def _get_family_chorelogs(
        page: int, limit: int, user: User, async_session: AsyncSession
) -> list[ChoreLogShow]:
    async with async_session.begin():
        offset = (page - 1) * limit
        data_service = ChoreLogDataService(async_session)
        result = await data_service.get_family_choreslogs(user.family_id, offset, limit)
        return result

async def _get_family_chorelog_detail(
        chorelog_id: UUID, user: User, async_session: AsyncSession
) -> ChoreLogDetailShow:
    async with async_session.begin():
        data_service = ChoreLogDataService(async_session)
        result = await data_service.get_family_choreslog_detail(chorelog_id)
        return result