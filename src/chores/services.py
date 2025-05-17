from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores.repository import AsyncChoreDAL
from chores.schemas import ChoreCreateSchema
from core.load_seed_data import load_seed_data
from core.services import BaseService
from families.models import Family


@dataclass
class ChoreCreatorService(BaseService[Chore | list[Chore]]):
    """Create and return a new Family"""

    family: Family
    db_session: AsyncSession
    data: ChoreCreateSchema | list[ChoreCreateSchema]

    async def process(self) -> Chore | list[Chore]:
        return await self._create_chores()

    async def _create_chores(self) -> Chore | list[Chore]:
        chore_dal = AsyncChoreDAL(self.db_session)
        if isinstance(self.data, list):
            return await chore_dal.create_chores_many(self.family.id, self.data)
        else:
            return await chore_dal.create(
                Chore(
                    name=self.data.name,
                    description=self.data.description,
                    icon=self.data.icon,
                    valuation=self.data.valuation,
                    family_id=self.family.id,
                )
            )


def get_default_chore_data() -> list[ChoreCreateSchema]:
    chores = load_seed_data()
    data = []
    for chore in chores:
        data.append(
            ChoreCreateSchema(
                name=chore["name"],
                description=chore["description"],
                icon=chore["icon"],
                valuation=chore["valuation"],
            )
        )
    return data
