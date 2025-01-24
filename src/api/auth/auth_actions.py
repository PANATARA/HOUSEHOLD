from typing import Union
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import auth_token
from db.dals.users import AsyncUserDAL
from db.models import User
from db.session import get_db
from hashing import Hasher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")


async def _get_user_by_username_for_auth(username: str, session: AsyncSession):
    async with session.begin():
        user_dal = AsyncUserDAL(session)
        return await user_dal.get_user_by_username(username=username)


async def authenticate_user(username: str, password: str, db: AsyncSession) -> Union[User, None]:
    
    user = await _get_user_by_username_for_auth(username=username, session=db)
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
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await _get_user_by_username_for_auth(username=username, session=db)
    if user is None:
        raise credentials_exception
    return user