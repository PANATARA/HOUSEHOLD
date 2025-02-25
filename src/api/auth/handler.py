from datetime import timedelta
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from config import auth_token
from api.auth.auth_actions import authenticate_user
from db.dals.families import AsyncFamilyDAL
from schemas.auth import Token
from db.session import get_db
from core.security import create_access_token

login_router = APIRouter()


@login_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):

    user = await authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=auth_token.ACCESS_TOKEN_EXPIRE_MINUTES)

    if user.family_id is not None:
        async with db.begin():
            family_dal = AsyncFamilyDAL(db_session=db)
            user_is_family_admin = await family_dal.user_is_family_admin(
                user_id=user.id, family_id=user.family_id
            )
    else:
        user_is_family_admin = False
    access_token = create_access_token(
        data={"sub": str(user.id), "is_family_admin": user_is_family_admin},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}
