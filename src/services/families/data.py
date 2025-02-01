from uuid import UUID
from dataclasses import dataclass
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.families import AsyncFamilyDAL
from schemas.families import FamilyFullShow
from schemas.users import ShowUser


@dataclass
class FamilyDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_with_users(self, family_id: UUID) -> FamilyFullShow | None:
        """Returns a pydantic model of the family and its members"""
        family_dal = AsyncFamilyDAL(self.db_session)
        rows = await family_dal.get_family_with_users(family_id)
        
        if rows is None:
            return None

        family_data = rows[0]
        users = [
            {
                "id": row["user_id"],
                "username": row["user_username"],
                "name": row["user_name"],
                "surname": row["user_surname"],
            }
            for row in rows
        ]
        user_adapter = TypeAdapter(list[ShowUser])
        members = user_adapter.validate_python(users)

        return FamilyFullShow(name=family_data["family_name"], members=members)
