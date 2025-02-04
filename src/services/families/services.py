from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import BaseService
from db.dals.families import AsyncFamilyDAL
from db.dals.users import AsyncUserDAL
from db.models.family import Family
from db.models.user import User
from db.models.wallet import Wallet
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
        return family
    
    async def _create_family(self) -> Family:
        family_dal = AsyncFamilyDAL(self.db_session)
        new_family = await family_dal.create_family(self.name)
        return new_family

    async def _add_user_to_family(self, family: Family) -> None:
        new_member = AddUserToFamilyService(family, self.user, self.db_session)
        await new_member()

    async def _create_default_family_chore(self, family: Family) -> None:
        data = await get_default_chore_data()
        default_chores = FamilyChoreCreatorService(family, self.db_session, data)
        return await default_chores()

    async def validate(self):
        "Validate the user is not a member of any family"
        return
    
@dataclass
class AddUserToFamilyService(BaseService):
    """Create and return a new Family"""
    family: Family
    user: User
    db_session: AsyncSession

    async def execute(self) -> Family:
        await self._add_user_to_family()
        await self._create_user_wallet()
        return self.family

    async def _add_user_to_family(self) -> Family:
        user_dal = AsyncUserDAL(self.db_session)
        await user_dal.update(self.user, {"family_id" : self.family.id})

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