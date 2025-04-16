import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from users.schemas import UserCreateSchema


CLEAN_TABLES = [
    "users",
]
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    default="postgresql+asyncpg://test:test@test_db:5432/postgres",
)

@pytest_asyncio.fixture
async def async_session_test():
    engine = create_async_engine(
        url=TEST_DATABASE_URL,
        future=True,
        echo=True,
        execution_options={"isolation_level": "REPEATABLE READ"},
    )

    async_session_factory = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession, autocommit=False
    )

    async with async_session_factory() as session:
        yield session

@pytest.fixture
def user_create_data() -> UserCreateSchema:
    return UserCreateSchema(
        username="test_username",
        name="testname",
        surname="testsurname",
        password="HouseHold-Password-2025",
    )