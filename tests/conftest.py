import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


CLEAN_TABLES = [
    "users",
]
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    default="postgresql+asyncpg://test:test@test_db:5432/postgres",
)

@pytest_asyncio.fixture
async def async_session_test():
    """Фикстура для создания сессии и её закрытия после теста."""
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
