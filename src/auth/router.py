from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth.actions import authenticate_user
from auth.schemas import AccessRefreshTokens, AccessToken, RefreshToken
from config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from core.exceptions.users import UserNotFoundError
from core.security import create_jwt_token, get_payload_from_jwt_token
from database_connection import get_db
from families.repository import AsyncFamilyDAL
from users.repository import AsyncUserDAL

router = APIRouter()


@router.post("/token", response_model=AccessRefreshTokens, tags=["Auth"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):

    user = await authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    if user.family_id is not None:
        async with db.begin():
            family_dal = AsyncFamilyDAL(db_session=db)
            user_is_family_admin = await family_dal.user_is_family_admin(
                user_id=user.id, family_id=user.family_id
            )
    else:
        user_is_family_admin = False
    access_token = create_jwt_token(
        data={"sub": str(user.id), "is_family_admin": user_is_family_admin},
        expires_delta=access_token_expires,
    )

    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_jwt_token(
        data={"sub": str(user.id), "is_family_admin": user_is_family_admin},
        expires_delta=refresh_token_expires,
    )
    return AccessRefreshTokens(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/refresh", response_model=AccessToken, tags=["Auth"])
async def refresh_access_token(
    refresh_token: RefreshToken, db: AsyncSession = Depends(get_db)
):
    payload_refresh_token = get_payload_from_jwt_token(refresh_token.refresh_token)
    user_id = payload_refresh_token.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token, missing user_id",
        )

    async with db.begin():
        try:
            user = await AsyncUserDAL(db).get_or_raise(object_id=user_id)
            family_dal = AsyncFamilyDAL(db_session=db)
            user_is_family_admin = await family_dal.user_is_family_admin(
                user_id=user.id, family_id=user.family_id
            )
        except UserNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_jwt_token(
        data={"sub": str(user_id), "is_family_admin": user_is_family_admin},
        expires_delta=access_token_expires,
    )
    return AccessToken(access_token=access_token, token_type="bearer")
