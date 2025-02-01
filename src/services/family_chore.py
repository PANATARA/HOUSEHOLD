from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.load_seed_data import load_seed_data
from core.services import BaseService
from db.dals.chores import AsyncChoreDAL
from db.models.family import Family
from schemas.chores import ChoreCreate

@dataclass
class FamilyChoreCreatorService(BaseService):
    """Create and return a new Family"""
    family: Family | UUID
    db_session: AsyncSession
    data: list[ChoreCreate]

    async def execute(self) -> None:
        await self._create_chores()
    
    async def _create_chores(self):
        chore_dal = AsyncChoreDAL(self.db_session)
        return await chore_dal.create_chores_many(
            self.family.id, 
            self.data
        )
    
async def get_default_chore_data() -> list[ChoreCreate]:
    chores = await load_seed_data("seed_data.json")
    data = []
    for chore in chores:
        data.append(ChoreCreate(
            name=chore["name"],
            description=chore["description"],
            icon=chore["icon"],
            valuation=chore["valuation"]
        ))
    return data