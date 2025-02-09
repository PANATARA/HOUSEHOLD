from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import BaseService
from core import constants
from db.dals.families import AsyncFamilyDAL
from db.dals.families_settings import AsyncFamilySettingsDAL
from db.dals.users import AsyncUserDAL, AsyncUserFamilyPermissionsDAL
from db.models.family import Family
from db.models.user import User, UserFamilyPermissions
from db.models.wallet import Wallet
from schemas.users import UserFamilyPermissionModel
from services.chores.family_chore import FamilyChoreCreatorService, get_default_chore_data
from services.wallets.services import WalletCreatorService


@dataclass
class FamilyCreatorService(BaseService):
    """Create and return a new Family"""
    name: str
    user: User | UUID # User who creates a family
    db_session: AsyncSession

    async def execute(self) -> Family:
        family = await self._create_family()
        await self._add_user_to_family(family)
        await self._create_default_family_chore(family)
        await self._create_family_settings(family.id)
        return family
    
    async def _create_family(self) -> Family:
        family_dal = AsyncFamilyDAL(self.db_session)
        new_family = await family_dal.create({"name": self.name})
        return new_family

    async def _add_user_to_family(self, family: Family) -> None:
        new_member = AddUserToFamilyService(
            family=family, 
            user=self.user,
            permissions=UserFamilyPermissionModel(**constants.default_admin_permissions),
            is_family_admin=True,
            db_session=self.db_session
        )
        await new_member()

    async def _create_default_family_chore(self, family: Family) -> None:
        data = await get_default_chore_data()
        default_chores = FamilyChoreCreatorService(family, self.db_session, data)
        return await default_chores()

    async def _create_family_settings(self, family_id: UUID) -> None:
        settings_dal = AsyncFamilySettingsDAL(self.db_session)
        await settings_dal.create({"family_id": family_id})

    async def validate(self):
        "Validate the user is not a member of any family"
        return
    
@dataclass
class AddUserToFamilyService(BaseService):
    """Create and return a new Family"""
    family: Family
    user: User
    permissions: UserFamilyPermissionModel
    is_family_admin: bool
    db_session: AsyncSession

    async def execute(self) -> Family:
        await self._add_user_to_family()
        await self._create_user_wallet()
        await self._create_permissions(self.permissions)
        return self.family

    async def _add_user_to_family(self) -> Family:
        user_dal = AsyncUserDAL(self.db_session)
        await user_dal.update(self.user, {"family_id" : self.family.id, "is_family_admin": self.is_family_admin})

    async def _create_permissions(self, fields: dict) -> UserFamilyPermissions:
        perm_dal = AsyncUserFamilyPermissionsDAL(self.db_session)
        fields = self.permissions.model_dump()
        fields["user_id"] = self.user.id
        return await perm_dal.create(fields)

    async def _create_user_wallet(self) -> Wallet:
        user_wallet = WalletCreatorService(self.user, self.db_session)
        return await user_wallet()

    async def validate(self):
        "Validate the user is not a member of any family"
        if self.user.family_id is not None:
            raise ValueError("The user is already a member of a family")


@dataclass
class LogoutUserFromFamilyService(BaseService):
    """Logout user from family"""
    family: Family
    user: User
    db_session: AsyncSession

    async def execute(self) -> None:
        pass

    async def _delete_user_wallet(self) -> None:
        pass

    async def validate(self):
       pass