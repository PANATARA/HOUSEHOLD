from typing import Any

from fastapi import Depends, Request
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_confirmations.models import ChoreConfirmation
from core.exceptions.http_exceptions import permission_denided
from products.models import Product
from users.models import User, UserFamilyPermissions
from users.repository import AsyncUserDAL
from auth.actions import oauth2_scheme
from core.security import get_payload_from_jwt_token
from database_connection import get_db


class BasePermission:
    """
    Base permission class to be inherited by all custom permissions.
    Defines the interface for checking user permissions and extracting the user.
    """

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


class IsAuthenicatedPermission(BasePermission):
    """
    Permission that verifies the user is authenticated and exists in the database.
    """

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
    """
    Permission that checks if the authenticated user is a member of a family.
    If `only_admin=True`, the user must also be a family admin.
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

        user = await super().get_user_and_check_permission(
            token_payload=token_payload,
            http_method=http_method,
            async_session=async_session,
            **kwargs,
        )

        if user.family_id is None:
            raise permission_denided
        return user


class FamilyUserAccessPermission(BasePermission):
    """
    Permission that verifies the user has access to another user from the same family.
    If `only_admin=True`, only family admins are allowed.
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

        target_user_id = kwargs.get("user_id")
        current_user_id = token_payload.get("sub")
        TargetUser = aliased(User)

        query = select(User).where(
            User.id == current_user_id,
            exists().where(
                (TargetUser.id == target_user_id)
                & (TargetUser.family_id == User.family_id)
            ),
        )

        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        return user


class ChorePermission(BasePermission):
    """
    Permission that checks whether the user has access to a specific chore in their family.
    If `only_admin=True`, access is granted only to family admins.
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
    """
    Permission that checks whether the user has access to a specific chore completion record
    through shared family association.
    """

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
    """
    Permission that verifies the user is related to the specified chore confirmation.
    Only the user who created the confirmation has access.
    """

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
    """
    Permission that checks if the user has access to a product belonging to their family.
    """

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
                (Product.family_id == User.family_id) & (Product.id == product_id)
            ),
        )

        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided
        return user


class FamilyInvitePermission(BasePermission):
    """
    Permission that checks if the user has rights to invite others into the family.
    Requires both a specific invite permission and admin role.
    """

    async def get_user_and_check_permission(
        self,
        token_payload: dict[str, Any],
        http_method: str,
        async_session: AsyncSession,
        **kwargs,
    ) -> User:
        user_id = token_payload.get("sub")
        permission_exists = (
            select(UserFamilyPermissions)
            .where(
                (UserFamilyPermissions.user_id == user_id)
                & (UserFamilyPermissions.can_invite_users.is_(True))
            )
            .exists()
        )

        query = select(User).where((User.id == user_id) & permission_exists)
        result = await async_session.execute(query)
        user = result.scalars().first()

        if user is None:
            raise permission_denided

        user_is_family_admin = token_payload.get("is_family_admin")
        if not user_is_family_admin:
            raise permission_denided

        return user
