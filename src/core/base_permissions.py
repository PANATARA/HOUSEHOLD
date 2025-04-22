from typing import Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth.actions import oauth2_scheme
from core.security import get_payload_from_jwt_token
from database_connection import get_db
from users.models import User


class BasePermission:

    async def __call__(
        self,
        request: Request,
        token: str = Depends(oauth2_scheme),
        async_session: AsyncSession = Depends(get_db),
    ) -> User:
        token_payload = get_payload_from_jwt_token(token)
        async with async_session.begin():
            user = await self.get_user_and_check_permission(
                token_payload=token_payload,
                http_method=request.method,
                async_session=async_session,
                **request.path_params,
            )
        return user

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:
        raise NotImplementedError
