from uuid import UUID
from dataclasses import dataclass
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.family import Family
from db.models.user import User
from schemas.families import FamilyFullShow
from schemas.users import UserResponse


@dataclass
class FamilyDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_with_users(self, family_id: UUID) -> FamilyFullShow | None:
        """Returns a pydantic model of the family and its members"""
        result = await self.db_session.execute(
            select(
                Family.id.label("family_id"),
                Family.name.label("family_name"),
                User.id.label("user_id"),
                User.username.label("user_username"),
                User.name.label("user_name"),
                User.surname.label("user_surname"),
            )
            .join(User, Family.id == User.family_id)
            .where(Family.id == family_id)
        )

        rows = result.mappings().all()
        
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
        user_adapter = TypeAdapter(list[UserResponse])
        members = user_adapter.validate_python(users)

        return FamilyFullShow(name=family_data["family_name"], members=members)
