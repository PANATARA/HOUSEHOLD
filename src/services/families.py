from uuid import UUID
from dataclasses import dataclass
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import BaseService
from db.dals.families import AsyncFamilyDAL
from db.dals.users import AsyncUserDAL
from db.models.family import Family
from db.models.user import User

@dataclass
class FamilyCreatorService(BaseService):
    """Create and return a new Family"""
    name: str
    user: User | UUID
    db_session: AsyncSession

    async def execute(self) -> Family:
        family = await self._create_family()
        family = await self._add_user_to_family(family)
        family = await self._create_default_family_chore(family)
        return family
    
    async def _create_family(self) -> Family:
        family_dal = AsyncFamilyDAL(self.db_session)
        new_family = await family_dal.create_family(self.name)
        return new_family

    async def _add_user_to_family(self, family: Family) -> Family:
        family = await AddUserToFamilyService(family, self.user, self.db_session)()
        return family


    async def _create_default_family_chore(self, family: Family) -> None:
        return family

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
        return self.family

    async def _add_user_to_family(self) -> Family:
        user_dal = AsyncUserDAL(self.db_session)
        await user_dal.update(self.user, {"family_id" : self.family.id})

    async def _create_user_wallet(self):
        pass

    async def validate(self):
        "Validate the user is not a member of any family"
        if self.user.family_id is not None:
            raise ValueError("The user is already a member of a family")