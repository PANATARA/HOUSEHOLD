from datetime import datetime, timezone
from datetime import timedelta
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from starlette import status

from config import auth_token
from core.exceptions import credentials_exception

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=auth_token.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, auth_token.SECRET_KEY, algorithm=auth_token.ALGORITHM)

def get_payload_from_jwt_token(token: str):
    try:
        payload = jwt.decode(
            token, auth_token.SECRET_KEY, algorithms=[auth_token.ALGORITHM]
        )
    except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token has expired",
            )
    except JWTError:
        raise credentials_exception
    else:
        return payload
