from typing import Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.family import Family
from db.models.user import User
from sqlalchemy import select

@dataclass
class AsyncUserDAL:
    # AsyncUserRepository:
    # AsyncUserManager:
    # UserDataService:
    db_session: AsyncSession

    async def create_user(self, username: str, name: str, surname: str, hashed_password:str) -> User:
        new_user = User(
            username=username,
            name=name,
            surname=surname,
            hashed_password=hashed_password,
        )
        self.db_session.add(new_user)
        await self.db_session.flush()
        return new_user
    
    async def update(self, user: User, fields: dict) -> User:
        for field, value in fields.items():
            if value is not None:
                setattr(user, field, value)
        self.db_session.add(user)
        await self.db_session.flush()
        return user

    async def get_user_by_id(self, user_id: UUID) -> Union[User, None]:
        query = select(User).where(User.id == user_id)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        if user is not None:
            return user[0]

    async def get_user_by_username(self, username: str) -> Union[User, None]:
        query = select(User).where(User.username == username)
        result = await self.db_session.execute(query)
        user = result.fetchone()
        if user is not None:
            return user[0]
