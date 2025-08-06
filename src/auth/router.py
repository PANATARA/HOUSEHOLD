import asyncio
import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.schemas import (
    AccessRefreshTokens,
    AccessToken,
    AuthCodeEmail,
    AuthEmail,
    RefreshToken,
)
from auth.services import send_email_secret_code
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    MAX_VERIFY_CODE,
    MIN_VERIFY_CODE,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)
from core.exceptions.users import UserNotFoundError
from core.redis_connection import redis_client
from core.security import create_jwt_token, get_payload_from_jwt_token
from database_connection import get_db
from families.repository import AsyncFamilyDAL
from users.repository import AsyncUserDAL
from users.services import UserCreatorService

router = APIRouter()


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
            user = await AsyncUserDAL(db).get_by_id(object_id=user_id)
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


@router.post("/request-code", tags=["Auth"])
async def send_email_code(body: AuthEmail) -> JSONResponse:
    secret_code = random.randint(MIN_VERIFY_CODE, MAX_VERIFY_CODE)

    redis = redis_client.get_client()
    await redis.set(body.email, secret_code, ex=300)

    asyncio.create_task(
        send_email_secret_code(to_email=body.email, secret_code=secret_code)
    )

    return JSONResponse(content="OK", status_code=201)


@router.post("/verify-code", tags=["Auth"])
async def post_email_code(
    body: AuthCodeEmail, db: AsyncSession = Depends(get_db)
) -> AccessRefreshTokens:
    redis = redis_client.get_client()
    code_from_redis = await redis.get(body.email)

    if code_from_redis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verify code was not found",
        )
    if int(code_from_redis) != body.code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect secret code",
        )
    is_new_user = False

    async with db.begin():
        try:
            user = await AsyncUserDAL(db).get_user_by_email(email=body.email)
        except UserNotFoundError:
            user = await UserCreatorService(
                email=body.email, db_session=db
            ).run_process()
            is_new_user = True

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        if user.family_id is not None:
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
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_new_user=is_new_user,
        is_family_member=bool(user.family_id),
    )


from pydantic import BaseModel  # noqa: E402


class DebugAuthModel(BaseModel):
    email: str


@router.post("/debug-auth", tags=["Auth"])
async def debug_auth_by_email(
    body: DebugAuthModel, db: AsyncSession = Depends(get_db)
) -> AccessRefreshTokens:
    async with db.begin():
        try:
            user = await AsyncUserDAL(db).get_user_by_email(email=body.email)
        except UserNotFoundError:
            raise HTTPException(status_code=404, detail="User was not found")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        if user.family_id is not None:
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
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_new_user=False,
        is_family_member=bool(user.family_id),
    )
