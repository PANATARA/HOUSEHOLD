import uuid
from typing import Union
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.family import Family
from sqlalchemy import select

@dataclass
class AsyncFamilyDAL:
    db_session: AsyncSession

    async def create_family(self, name: str) -> Family:
        family = Family(name=name)
        self.db_session.add(family)
        await self.db_session.flush()
        return family
    
    async def update(self, new_name: str, family_id: uuid.UUID) -> Family:
        pass

    async def get_family_by_id(self, family_id: uuid.UUID) -> Union[Family, None]:
        query = select(Family).where(Family.id == family_id)
        result = await self.db_session.execute(query)
        family = result.fetchone()
        if family is not None:
            return family[0]
