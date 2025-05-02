from uuid import UUID

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.hashing import Hasher
from users.models import User
from users.repository import AsyncUserDAL

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login/token")


async def _get_user_by_id_for_auth(user_id: UUID, session: AsyncSession):
    async with session.begin():
        user_dal = AsyncUserDAL(session)
        return await user_dal.get_by_id(user_id)


async def authenticate_user(
    username: str, password: str, db: AsyncSession
) -> User | None:

    async with db.begin():
        user_dal = AsyncUserDAL(db)
        user = await user_dal.get_user_by_username(username=username)
        if user is None:
            return
        if not Hasher.verify_password(password, user.password):
            return
        return user
