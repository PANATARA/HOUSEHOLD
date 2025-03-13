from typing import Any
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import SAFE_METHODS
from core.permissions import BasePermission
from db.dals.users import AsyncUserDAL
from db.models import User
from db.models.chore import Chore, ChoreCompletion, ChoreConfirmation
from core.exceptions.http_exceptions import permission_denided, user_not_found, credentials_exception
from db.models.user import UserFamilyPermissions


class IsAuthenicatedPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:

        user_id = token_payload.get("sub")
        if user_id is None:
            raise permission_denided
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.get_or_raise(user_id)
        
        return user


class FamilyMemberPermission(IsAuthenicatedPermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs) -> User:

        user = await super().get_user_and_check_permission(
            token_payload = token_payload,
            http_method = http_method,
            async_session = async_session,
            **kwargs
        )
        
        if user.family_id is None:
            raise permission_denided
        return user


class IsFamilyAdminPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:
        user_is_family_admin = token_payload.get("is_family_admin")
        if not user_is_family_admin:
            raise permission_denided
        user_id = token_payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.get_by_id(user_id)

        if user is None:
            raise user_not_found
        return user


class ChorePermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
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
        token_payload: dict[str, Any],
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
        token_payload: dict[str, Any],
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
    

class FamilyInvitePermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs
    ) -> User:

        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists().where(
                (UserFamilyPermissions.user_id == user_id) &
                (UserFamilyPermissions.can_invite_users == True)  # noqa: E712
            ).correlate(User)
        )
        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        
        user_is_family_admin = token_payload.get("is_family_admin")
        if not user_is_family_admin:
            raise permission_denided
        
        return user
