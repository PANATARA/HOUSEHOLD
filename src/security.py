from datetime import datetime, timezone
from datetime import timedelta
from jose import jwt

from config import auth_token

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