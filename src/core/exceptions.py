from fastapi import HTTPException
from starlette import status

class UserCannotLeaveFamily(Exception):
    pass


class NoSuchUserFoundInThefamily(Exception):
    pass


class NotEnoughCoins(Exception):
    pass


permission_denided = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Forbidden",
)

user_not_found =  HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Such user not found",
)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)