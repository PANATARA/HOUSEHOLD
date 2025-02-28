from uuid import UUID
from fastapi import Depends
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.actions import oauth2_scheme
from core.constants import SAFE_METHODS
from core.permissions import BasePermission
from core.security import get_payload_from_jwt_token
from db.dals.users import AsyncUserDAL
from db.models import User
from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from db.session import get_db
from core.exceptions import permission_denided, user_not_found


async def get_user_and_check_is_family_admin(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:

    payload = get_payload_from_jwt_token(token)

    user_id: UUID = payload.get("sub")
    user_is_family_admin: bool = payload.get("is_family_admin")
    if not user_is_family_admin:
        raise permission_denided

    async with db.begin():
        user_dal = AsyncUserDAL(db)
        user = await user_dal.get_by_id(user_id)

    if user is None:
        raise user_not_found
    return user


class IsAuthenicatedPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:

        user_id = token_payload.get("sub")
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.get_by_id(user_id)

        if user is None:
            raise user_not_found
        return user


class IsFamilyAdminPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:
        user_is_family_admin = token_payload.get("is_family_admin")
        if not user_is_family_admin:
            raise permission_denided
        user_id = token_payload.get("sub")
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.get_by_id(user_id)

        if user is None:
            raise user_not_found
        return user


class ChorePermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:
        user_is_family_admin = token_payload.get("is_family_admin")
        if http_method not in SAFE_METHODS and not user_is_family_admin:
            raise permission_denided

        chore_id = kwargs.get("chore_id")
        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists().where(
                (Chore.id == chore_id) & (User.family_id == Chore.family_id)
            ),
        )

        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        return user


class ChoreCompletionPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:

        chore_completion_id = kwargs.get("chore_completion_id")
        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists().where(
                (ChoreCompletion.id == chore_completion_id)
                & (ChoreCompletion.chore_id == Chore.id)
                & (User.family_id == Chore.family_id)
            ),
        )

        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        return user


class ChoreConfirmationPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:

        chore_confirmation_id = kwargs.get("chore_confirmation_id")
        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists().where(
                (ChoreConfirmation.user_id == User.id)
                & (ChoreConfirmation.id == chore_confirmation_id)
            ),
        )

        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        return user
