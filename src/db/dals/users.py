from sqlalchemy.ext.asyncio import AsyncSession

from db.models.users import User

class UserDAL:

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(self, username: str, name: str, surname: str) -> User:
        new_user = User(
            username=username,
            name=name,
            surname=surname,
        )
        self.db_session.add(new_user)
        await self.db_session.flush()
        return new_user