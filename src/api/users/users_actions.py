from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.users import ShowUser, UserCreate, UserSettingsShow, UserUpdate
from db.dals.users import AsyncUserDAL
from logging import getLogger

from db.models.user import User
from services.users.data import UserDataService
from services.users.services import UserCreatorService

logger = getLogger(__name__)

user_router = APIRouter()

async def _create_new_user(body: UserCreate, async_session: AsyncSession) -> ShowUser:
    async with async_session.begin():
        service = UserCreatorService(
            username = body.username,
            name = body.name,
            surname = body.surname,
            password = body.password,
            db_session=async_session,
        )
        user = await service()
        return ShowUser(
            id=user.id,
            username=user.username,
            name=user.name,
            surname=user.surname,
        )


async def show_user(user: User) -> ShowUser:
    return ShowUser(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
    )

async def _update_user(user: User, body: UserUpdate, async_session: AsyncSession) -> ShowUser:
    async with async_session.begin():
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.update(
            user=user,
            fields=body.model_dump()
        )
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
    

async def _get_me_settings(user: User, async_session: AsyncSession) -> UserSettingsShow:
    async with async_session.begin():
        data_service = UserDataService(async_session)
        return await data_service.get_user_settings(
            user=user
        )    