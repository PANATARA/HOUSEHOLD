import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database_connection import get_db
from families.services import AddUserToFamilyService, FamilyCreatorService
from users.schemas import UserCreateSchema, UserFamilyPermissionModelSchema
from users.services import UserCreatorService
from main import app


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
    "DATABASE_URL",
    default="postgresql+asyncpg://test:test@test_db:5432/postgres",
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    yield engine
    await engine.dispose()


@pytest.fixture
def async_session_factory(db_engine):
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def override_get_db(async_session_factory):
    async def _get_db_override():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def async_session_test(async_session_factory):
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_tables(async_session_test):
    async with async_session_test.begin():
        for table_for_cleaning in CLEAN_TABLES:
            await async_session_test.execute(
                text(f"TRUNCATE TABLE {table_for_cleaning} CASCADE")
            )


@pytest_asyncio.fixture
async def user_factory(async_session_test: AsyncSession):
    async def _create_user(
        username="ivnivn",
        name="Ivan",
        surname="Ivanov",
        password="PasswordIvanov2000",
    ):
        user_data = UserCreateSchema(
            username=username,
            name=name,
            surname=surname,
            password=password,
        )
        service = UserCreatorService(user_data=user_data, db_session=async_session_test)
        return await service.run_process()

    return _create_user


@pytest_asyncio.fixture
async def admin_family(async_session_test, user_factory):
    user = await user_factory()
    service = FamilyCreatorService(
        name="family_test", user=user, db_session=async_session_test
    )
    family = await service.run_process()
    await async_session_test.commit()
    return user, family


@pytest_asyncio.fixture
async def member_family(admin_family, async_session_test, user_factory):
    _, family = admin_family

    user = await user_factory(
        username="megapetr",
        name="Petr",
        surname="Petrov",
        password="PasswordPetrov2000",
    )

    user_permissions = UserFamilyPermissionModelSchema(
        should_confirm_chore_completion=True
    )
    await AddUserToFamilyService(
        family, user, user_permissions, async_session_test
    ).run_process()
    await async_session_test.commit()
    await async_session_test.refresh(user)
    return user, family
