from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.chores import ChoreCreate, ChoreShow, ChoresResponse


from logging import getLogger

from services.chores.data import ChoreDataService
from services.chores.family_chore import FamilyChoreCreatorService
logger = getLogger(__name__)


async def _get_family_chore(family_id: UUID, async_session: AsyncSession) -> ChoresResponse:
    async with async_session.begin():
        
        return await ChoreDataService(async_session).get_family_chores(family_id)

async def _create_family_chore(body: ChoreCreate, family_id: UUID, async_session: AsyncSession) -> ChoreShow:
    async with async_session.begin():
        creator_service = FamilyChoreCreatorService(family_id, async_session, body)
        data = await creator_service()
        return ChoreShow(
            id=data.id,
            name=data.name,
            description=data.description,
            icon=data.icon,
            valuation=data.valuation
        )