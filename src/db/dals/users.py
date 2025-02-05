from typing import Union
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.user import User
from sqlalchemy import select

@dataclass
class AsyncUserDAL(BaseDals):
    db_session: AsyncSession

    class Meta:
        model = User

    async def get_user_by_username(self, username: str) -> Union[User, None]:
        query = select(User).where(User.username == username)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        if user is not None:
            return user[0]
