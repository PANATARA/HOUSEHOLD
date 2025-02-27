from typing import Union
from uuid import UUID
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.users import AsyncUserDAL
from db.models import User
from core.hashing import Hasher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login/token")


async def _get_user_by_id_for_auth(user_id: UUID, session: AsyncSession):
    async with session.begin():
        user_dal = AsyncUserDAL(session)
        return await user_dal.get_by_id(user_id)


async def authenticate_user(username: str, password: str, db: AsyncSession) -> Union[User, None]:
    
    async with db.begin():
        user_dal = AsyncUserDAL(db)
        user = await user_dal.get_user_by_username(username=username)
        if user is None:
            return
        if not Hasher.verify_password(password, user.hashed_password):
            return
        return user
    