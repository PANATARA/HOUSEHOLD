from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from schemas.chores_logs import ChoreConfirmation


from logging import getLogger

from services.chores.data import ChoreConfirmationDataService

logger = getLogger(__name__)


async def _get_my_chores_confirmations(user: User, async_session: AsyncSession) -> list[ChoreConfirmation]:
    async with async_session.begin():
        data_service = ChoreConfirmationDataService(db_session=async_session)
        result = await data_service.get_user_chore_confirmations(user.id)
        return result