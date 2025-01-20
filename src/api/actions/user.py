from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ShowUser, UserCreate
from db.dals.user import AsyncUserDAL
from logging import getLogger

from hashing import Hasher

logger = getLogger(__name__)

user_router = APIRouter()

async def _create_new_user(body: UserCreate, async_session: AsyncSession) -> ShowUser:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.create_user(
            username=body.username,
            name=body.name,
            surname=body.surname,
            hashed_password=Hasher.get_password_hash(body.password)
        )
        return ShowUser(
            user_id=user.id,
            username=user.username,
            name=user.name,
            surname=user.surname,
            is_active=user.is_active,
        )