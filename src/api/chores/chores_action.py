from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.chores import ChoresResponse


from logging import getLogger

from services.chores.data import ChoreDataService
logger = getLogger(__name__)


async def _get_family_chore(family_id: UUID, async_session: AsyncSession) -> ChoresResponse:
    async with async_session.begin():
        
        return await ChoreDataService(async_session).get_family_chores(family_id)