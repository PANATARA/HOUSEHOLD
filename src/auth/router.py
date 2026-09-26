from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.schemas import (
    AccessRefreshTokens,
    AccessToken,
    GoogleAuthSchema,
    LoginSchema,
    RefreshToken,
    RegisterSchema,
)
from auth.services import InvalidGoogleTokenError, verify_google_id_token
from config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from core.exceptions.users import UserNotFoundError
from core.hashing import Hasher
from core.security import create_jwt_token, get_payload_from_jwt_token
from database_connection import get_db
from families.repository import FamilyRepository
from users.models import User
from users.repository import UserRepository

router = APIRouter()


def _build_tokens(
    user: User, is_family_admin: bool, is_new_user: bool
) -> AccessRefreshTokens:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt_token(
        data={"sub": str(user.id), "is_family_admin": is_family_admin},
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_jwt_token(
        data={"sub": str(user.id), "is_family_admin": is_family_admin},
        expires_delta=refresh_token_expires,
    )
    return AccessRefreshTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_new_user=is_new_user,
        is_family_member=bool(user.family_id),
    )


@router.post(
    "/register",
    response_model=AccessRefreshTokens,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
)
async def register(
    body: RegisterSchema, db: AsyncSession = Depends(get_db)
) -> AccessRefreshTokens:
    username = body.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя не может быть пустым",
        )

    async with db.begin():
        user_repo = UserRepository(db)
        existing_user = await user_repo.get_by_username(username=username)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким логином уже существует",
            )

        hashed_password = Hasher.get_password_hash(body.password)
        user = await user_repo.create_user_with_password(
            username=username,
            hashed_password=hashed_password,
            name=body.name.strip() if body.name else None,
            icon=body.icon,
            icon_color=body.icon_color,
            icon_bg=body.icon_bg,
        )
        return _build_tokens(user, is_family_admin=False, is_new_user=True)


@router.post("/login", response_model=AccessRefreshTokens, tags=["Auth"])
async def login(
    body: LoginSchema, db: AsyncSession = Depends(get_db)
) -> AccessRefreshTokens:
    identifier = body.username.strip()
    async with db.begin():
        user_repo = UserRepository(db)
        user = await user_repo.get_by_username_or_email(identifier=identifier)
        if (
            user is None
            or not user.hashed_password
            or not Hasher.verify_password(body.password, user.hashed_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь деактивирован",
            )

        user_is_family_admin = False
        if user.family_id is not None:
            family_dal = FamilyRepository(db_session=db)
            user_is_family_admin = await family_dal.user_is_family_admin(
                user_id=user.id, family_id=user.family_id
            )

        return _build_tokens(
            user, is_family_admin=user_is_family_admin, is_new_user=False
        )


@router.post("/refresh", response_model=AccessToken, tags=["Auth"])
async def refresh_access_token(
    refresh_token: RefreshToken, db: AsyncSession = Depends(get_db)
) -> AccessToken:
    payload_refresh_token = get_payload_from_jwt_token(refresh_token.refresh_token)
    user_id = payload_refresh_token.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token, missing user_id",
        )

    async with db.begin():
        try:
            user = await UserRepository(db).get_by_id(object_id=user_id)
            family_dal = FamilyRepository(db_session=db)
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


@router.post("/google", response_model=AccessRefreshTokens, tags=["Auth"])
async def google_auth(
    body: GoogleAuthSchema, db: AsyncSession = Depends(get_db)
) -> AccessRefreshTokens:
    token = body.get_token()
    try:
        id_info = await verify_google_id_token(token)
    except InvalidGoogleTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Google token: {str(e)}",
        )

    sub = id_info.get("sub")
    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token does not contain an email address",
        )

    name = id_info.get("given_name") or id_info.get("name")

    async with db.begin():
        user_repo = UserRepository(db)
        user, is_new_user = await user_repo.upsert_google_user(
            sub=sub,
            email=email,
            name=name,
        )

        user_is_family_admin = False
        if user.family_id is not None:
            family_dal = FamilyRepository(db_session=db)
            user_is_family_admin = await family_dal.user_is_family_admin(
                user_id=user.id, family_id=user.family_id
            )

        return _build_tokens(
            user, is_family_admin=user_is_family_admin, is_new_user=is_new_user
        )
