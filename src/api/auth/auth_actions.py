from typing import Union
from uuid import UUID
from fastapi import Depends, Request
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import auth_token
from db.dals.users import AsyncUserDAL
from db.models import User
from db.models.chore import Chore, ChoreCompletion
from db.session import get_db
from core.hashing import Hasher
from core.exceptions import permission_denided

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


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(
            token, auth_token.SECRET_KEY, algorithms=[auth_token.ALGORITHM]
        )
        user_id: UUID = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await _get_user_by_id_for_auth(user_id=user_id, session=db)
    if user is None:
        raise credentials_exception
    return user

def get_user_id_from_token(
    token: str = Depends(oauth2_scheme)
) -> UUID | HTTPException:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(
            token, auth_token.SECRET_KEY, algorithms=[auth_token.ALGORITHM]
        )
        user_id: UUID = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id
    