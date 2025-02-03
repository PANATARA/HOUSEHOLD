from uuid import UUID
from dataclasses import dataclass
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.chores import AsyncChoreDAL
from db.dals.families import AsyncFamilyDAL
from schemas.chores import ChoreShow, ChoresResponse
from schemas.families import FamilyFullShow
from schemas.users import ShowUser


@dataclass
class ChoreDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_chores(self, family_id: UUID):
        """Returns a pydantic model of the chores"""
        chore_dal = AsyncChoreDAL(self.db_session)
        rows = await chore_dal.get_family_chores(family_id)

        if not rows:
            return None

        chores = [
            ChoreShow(
                id=row["chore_id"],
                name=row["chore_name"],
                description=row["chore_description"],
                icon=row["chore_icon"],
                valuation=row["chore_valuation"],
            )
            for row in rows
        ]
        
        return ChoresResponse(chores=chores)
