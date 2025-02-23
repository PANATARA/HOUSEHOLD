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