from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ShowUser, UserCreate
from db.dals.user import AsyncUserDAL
from db.session import get_db
from logging import getLogger

from hashing import Hasher

logger = getLogger(__name__)

user_router = APIRouter()

async def _create_new_user(body: UserCreate, db) -> ShowUser:
    async with db as session:
        async with session.begin():
            user_dal = AsyncUserDAL(session)
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


@user_router.post("/", response_model=ShowUser)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> ShowUser:
    try:
        return await _create_new_user(body, db)
    except IntegrityError as err:
        logger.error(err)
        raise HTTPException(status_code=503, detail=f"Database error: {err}")
