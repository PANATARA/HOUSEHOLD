from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from starlette import status

import config
from core.exceptions.http_exceptions import credentials_exception


def create_jwt_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta

    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


def get_payload_from_jwt_token(token: str):
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token has expired",
        )
    except JWTError:
        raise credentials_exception
    else:
        return payload
