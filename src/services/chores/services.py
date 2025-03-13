from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.load_seed_data import load_seed_data
from core.services import BaseService
from db.dals.chores import AsyncChoreDAL
from db.models.chore import Chore
from db.models.family import Family
from schemas.chores.chores import NewChoreCreate

@dataclass
class ChoreCreatorService(BaseService):
    """Create and return a new Family"""
    family: Family
    db_session: AsyncSession
    data: NewChoreCreate | list[NewChoreCreate]

    async def process(self) -> Chore | list[Chore]:
        return await self._create_chores()
    
    async def _create_chores(self) -> Chore | list[Chore]:
        chore_dal = AsyncChoreDAL(self.db_session)
        if isinstance(self.data, list):
            return await chore_dal.create_chores_many(
                self.family.id, 
                self.data
            )
        else:
            return await chore_dal.create(
                fields={
                    "name": self.data.name,
                    "description": self.data.description,
                    "icon": self.data.icon,
                    "valuation": self.data.valuation,
                    "family_id": self.family,
                }
            )
    
async def get_default_chore_data() -> list[NewChoreCreate]:
    chores = await load_seed_data("seed_data.json")
    data = []
    for chore in chores:
        data.append(NewChoreCreate(
            name=chore["name"],
            description=chore["description"],
            icon=chore["icon"],
            valuation=chore["valuation"]
        ))
    return data