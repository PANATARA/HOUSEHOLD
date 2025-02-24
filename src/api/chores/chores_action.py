from uuid import UUID
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.chores import NewChoreCreate, NewChoreDetail, NewChoreSummary


from logging import getLogger

from schemas.users import UserResponse
from services.chores.data import ChoreDataService
from services.chores.services import ChoreCreatorService

logger = getLogger(__name__)


async def _get_family_chore(
    family_id: UUID, async_session: AsyncSession
) -> list[NewChoreSummary]:
    async with async_session.begin():

        return await ChoreDataService(async_session).get_family_chores(family_id)


async def _create_family_chore(
    body: NewChoreCreate, family_id: UUID, async_session: AsyncSession
) -> NewChoreDetail:
    async with async_session.begin():
        creator_service = ChoreCreatorService(
            family=family_id,
            db_session=async_session,
            data=body,
        )
        new_chore = await creator_service()
        return NewChoreDetail(
            id=new_chore.id,
            name=new_chore.name,
            description=new_chore.description,
            icon=new_chore.icon,
            valuation=new_chore.valuation,
            created_at=new_chore.created_at,
        )


async def _delete_family_chore(
    chore_id: UUID, family_id: UUID, async_session: AsyncSession
) -> Response:
    async with async_session.begin():

        return
