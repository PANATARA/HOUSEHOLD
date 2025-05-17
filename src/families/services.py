from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from chores.services import ChoreCreatorService, get_default_chore_data
from core.exceptions.families import UserCannotLeaveFamily
from core.services import BaseService
from core.validators import validate_user_not_in_family
from families.models import Family
from families.repository import AsyncFamilyDAL
from users.models import User, UserFamilyPermissions
from users.repository import AsyncUserDAL, AsyncUserFamilyPermissionsDAL
from users.schemas import UserFamilyPermissionModelSchema
from wallets.models import Wallet
from wallets.repository import AsyncWalletDAL
from wallets.services import WalletCreatorService


@dataclass
class FamilyCreatorService(BaseService[Family]):
    """Create and return a new Family"""

    name: str
    user: User  # User who creates a family
    db_session: AsyncSession

    async def process(self) -> Family:
        family = await self._create_family()
        await self._add_user_to_family(family)
        await self._create_default_family_chore(family)
        self._set_default_avatar()
        return family

    async def _create_family(self) -> Family:
        family_dal = AsyncFamilyDAL(self.db_session)
        new_family = await family_dal.create(
            Family(name=self.name, family_admin_id=self.user.id)
        )
        return new_family

    async def _add_user_to_family(self, family: Family) -> None:
        new_member = AddUserToFamilyService(
            family=family,
            user=self.user,
            permissions=UserFamilyPermissionModelSchema(
                should_confirm_chore_completion=True
            ),
            db_session=self.db_session,
        )
        await new_member.run_process()

    async def _create_default_family_chore(self, family: Family) -> None:
        data = get_default_chore_data()
        default_chores = ChoreCreatorService(family, self.db_session, data)
        return await default_chores.run_process()

    def _set_default_avatar(self) -> None:
        pass


@dataclass
class AddUserToFamilyService(BaseService[Family]):
    """Create and return a new Family"""

    family: Family
    user: User
    permissions: UserFamilyPermissionModelSchema
    db_session: AsyncSession

    async def process(self) -> Family:
        await self._add_user_to_family()
        await self._create_user_wallet()
        await self._create_permissions(self.permissions.model_dump())
        return self.family

    async def _add_user_to_family(self) -> None:
        user_dal = AsyncUserDAL(self.db_session)
        await user_dal.update(self.user.id, {"family_id": self.family.id})

    async def _create_permissions(self, fields: dict) -> UserFamilyPermissions:
        perm_dal = AsyncUserFamilyPermissionsDAL(self.db_session)
        fields = self.permissions.model_dump()
        fields["user_id"] = self.user.id
        return await perm_dal.create(fields)

    async def _create_user_wallet(self) -> Wallet:
        user_wallet = WalletCreatorService(self.user, self.db_session)
        return await user_wallet.run_process()

    def get_validators(self):
        return [lambda: validate_user_not_in_family(self.user)]


@dataclass
class LogoutUserFromFamilyService(BaseService[None]):
    """Logout user from family"""

    user: User
    db_session: AsyncSession

    async def process(self) -> None:
        await self._update_user_field()
        await self._delete_user_permissions()
        await self._delete_user_wallet()

    async def _update_user_field(self) -> None:
        user_dal = AsyncUserDAL(self.db_session)
        await user_dal.update(self.user.id, {"family_id": None})

    async def _delete_user_permissions(self) -> None:
        permissions_repo = AsyncUserFamilyPermissionsDAL(self.db_session)
        user_permission = await permissions_repo.get_by_user_id(self.user.id)
        await permissions_repo.hard_delete(user_permission.id)

    async def _delete_user_wallet(self) -> None:
        wallet_repo = AsyncWalletDAL(self.db_session)
        wallet = await wallet_repo.get_by_user_id(self.user.id)
        await wallet_repo.hard_delete(wallet.id)

    async def _delete_user_products(self) -> None:
        pass

    async def validate(self):
        family_dal = AsyncFamilyDAL(self.db_session)
        if await family_dal.user_is_family_admin(self.user.id, self.user.family_id):
            raise UserCannotLeaveFamily()
