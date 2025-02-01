from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.users import ShowUser, UserCreate, UserUpdate
from db.dals.users import AsyncUserDAL
from logging import getLogger

from db.models.user import User
from core.hashing import Hasher

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
            id=user.id,
            username=user.username,
            name=user.name,
            surname=user.surname,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )


async def show_user(user: User) -> ShowUser:
    return ShowUser(
        user_id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
        is_active=user.is_active,
    )

async def _update_user(user:User, body: UserUpdate, async_session: AsyncSession) -> ShowUser:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            user=user,
            fields=body.model_dump()
        )
        # import pdb; pdb.set_trace()
        return ShowUser(
            user_id=user.id,
            username=user.username,
            name=user.name,
            surname=user.surname,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            # updated_at=user.updated_at,
        )


async def _delete_user(user:User, async_session: AsyncSession) -> ShowUser:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        return