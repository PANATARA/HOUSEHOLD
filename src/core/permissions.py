from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_confirmations.models import ChoreConfirmation
from core.exceptions.http_exceptions import permission_denided
from core.base_permissions import BasePermission
from products.models import Product
from users.models import User, UserFamilyPermissions
from users.repository import AsyncUserDAL


class IsAuthenicatedPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:

        user_id = token_payload.get("sub")
        if user_id is None:
            raise permission_denided
        user_dal = AsyncUserDAL(async_session)
        user = await user_dal.get_or_raise(user_id)

        return user


class FamilyMemberPermission(IsAuthenicatedPermission):

    def __init__(self, only_admin: bool = False):
        self.only_admin = only_admin
        super().__init__()

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:
        
        if self.only_admin:
            user_is_family_admin = token_payload.get("is_family_admin")
            if not user_is_family_admin:
                raise permission_denided

        user = await super().get_user_and_check_permission(
            token_payload=token_payload,
            http_method=http_method,
            async_session=async_session,
            **kwargs,
        )

        if user.family_id is None:
            raise permission_denided
        return user


class ChorePermission(BasePermission):
    """
    Checking that the user has access to this **Chore**

    If http method not in SAFE_METHODS ("GET", "HEAD", "OPTIONS", "TRACE")
    then the administrator is also checked
    """
    def __init__(self, only_admin: bool = False):
        self.only_admin = only_admin
        super().__init__()

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:
        if self.only_admin:
            user_is_family_admin = token_payload.get("is_family_admin")
            if not user_is_family_admin:
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
        **kwargs,
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
        **kwargs,
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


class ProductPermission(BasePermission):

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:

        product_id = kwargs.get("product_id")
        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists().where(
                (Product.family_id == User.family_id)
                & (Product.id == product_id)
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
        **kwargs,
    ) -> User:

        user_id = token_payload.get("sub")
        query = select(User).where(
            User.id == user_id,
            exists()
            .where(
                (UserFamilyPermissions.user_id == user_id)
                & (UserFamilyPermissions.can_invite_users == True)  # noqa: E712
            )
            .correlate(User),
        )
        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided

        user_is_family_admin = token_payload.get("is_family_admin")
        if not user_is_family_admin:
            raise permission_denided

        return user
