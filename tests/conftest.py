import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from users.schemas import UserCreateSchema
from users.services import UserCreatorService


CLEAN_TABLES = [
    "users",
    "users_family_permissions",
    "users_settings",
    "wallets",
    "family",
    "chores",
    "chore_completion",
    "chore_confirmation",
    "peer_transactions",
    "product_buyers",
    "products",
    "reward_transactions",
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


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_tables(async_session_test):
    """Clean data in all tables before running test function"""
    async with async_session_test.begin():
        for table_for_cleaning in CLEAN_TABLES:
            await async_session_test.execute(
                text(f"TRUNCATE TABLE {table_for_cleaning} CASCADE")
            )


class UserFactory:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(
        self,
        username: str = "test_user",
        name: str = "Test",
        surname: str = "User",
        password: str = "StrongPassword123!",
    ):
        user_data = UserCreateSchema(
            username=username,
            name=name,
            surname=surname,
            password=password,
        )
        service = UserCreatorService(user_data=user_data, db_session=self.session)
        return await service.run_process()


@pytest.fixture
def user_factory(async_session_test: AsyncSession) -> UserFactory:
    return UserFactory(session=async_session_test)
