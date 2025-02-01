import uuid
from typing import Union
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.family import Family
from sqlalchemy import select

from db.models.user import User


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

    async def get_family_with_users(self, family_id: uuid.UUID) -> list[dict] | None:
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

        if not rows:
            return None
        return rows
