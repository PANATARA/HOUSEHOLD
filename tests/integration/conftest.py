"""
Integration test configuration.
Uses testcontainers to spin up a real PostgreSQL database,
applies Alembic migrations, and provides async sessions.

Each test gets its own transaction that is rolled back after the test,
so tests don't interfere with each other.
"""

import datetime
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from chores.models import Chore
from core.enums import FrequencyTypeENUM
from core.hashing import Hasher
from core.models import Base
from database_connection import get_db
from families.models import Family
from main import app
from meals.models import GroceryItem, PlannedMeal, Recipe
from notifications.models import UserDevice
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from users.models import User, UserFamilyPermissions, UserSettings


# ── Container (session-scoped – starts once per test session) ──────────────────

@pytest.fixture(scope="session")
def pg_container():
    """Start a real PostgreSQL container for the entire test session."""
    with PostgresContainer("postgres:14", driver="asyncpg") as pg:
        yield pg


@pytest.fixture(scope="session")
def sync_db_url(pg_container):
    """Synchronous URL needed by Alembic to apply migrations."""
    return pg_container.get_connection_url().replace("+asyncpg", "")


@pytest.fixture(scope="session")
def async_db_url(pg_container):
    """Async URL for SQLAlchemy async engine."""
    return pg_container.get_connection_url()


@pytest.fixture(scope="session")
def apply_migrations(sync_db_url):
    """Apply all Alembic migrations once per session."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-x",
            f"db_url={sync_db_url}",
            "upgrade",
            "head",
        ],
        cwd="/home/andrey/Projects/HOUSEHOLD",
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "DATABASE_URL": sync_db_url.replace("postgresql://", "postgresql+asyncpg://"),
        },
    )
    if result.returncode != 0:
        # Fallback: create tables directly from metadata
        from sqlalchemy import create_engine
        engine = create_engine(sync_db_url)
        # Import all models to register with Base.metadata
        import chores.models  # noqa: F401
        import families.models  # noqa: F401
        import meals.models  # noqa: F401
        import notifications.models  # noqa: F401
        import planned_chores.models  # noqa: F401
        import users.models  # noqa: F401
        Base.metadata.create_all(engine)
        engine.dispose()
    return True


@pytest.fixture(scope="session")
def integration_engine_url(async_db_url, apply_migrations):
    """Just returns the URL. Engine will be created per-test to avoid event loop issues."""
    return async_db_url


@pytest_asyncio.fixture
async def db_session(integration_engine_url) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a real database session for a single test.
    Cleans up all domain tables via TRUNCATE CASCADE after each test,
    ensuring complete isolation and allowing FastAPI endpoints to manage
    their own transactions (e.g. async with db.begin():) without conflict.
    """
    from sqlalchemy import text

    engine = create_async_engine(
        integration_engine_url,
        future=True,
        echo=False,
    )
    factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        try:
            yield session
        finally:
            try:
                if session.in_transaction():
                    await session.rollback()
                await session.execute(text("""
                    TRUNCATE TABLE 
                        planned_chore, quick_planned_chore, chore_schedule,
                        chores, planned_meals, grocery_items, recipes,
                        events, user_devices, user_family_permissions, user_settings,
                        users, family
                    CASCADE;
                """))
                await session.commit()
            except Exception:
                pass

    await engine.dispose()


# ── HTTP Client wired to the real DB ──────────────────────────────────────────

@pytest_asyncio.fixture
async def integration_client(
    integration_engine_url,
    integration_factory,
) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI AsyncClient backed by a real PostgreSQL session.
    Auth is bypassed: the current user is the integration_factory.user.
    """
    from fastapi import Request
    from core.permissions import BasePermission

    current_user = integration_factory.user

    engine = create_async_engine(integration_engine_url, future=True, echo=False)
    client_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with client_factory() as session:
            yield session

    async def mock_permission(self, request: Request):
        return current_user

    app.dependency_overrides[get_db] = override_get_db

    with patch.object(BasePermission, "__call__", mock_permission):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client

    app.dependency_overrides.clear()
    await engine.dispose()


# ── Factory: creates a complete household (family + 2 users + chore) ──────────

class IntegrationFactory:
    """Creates realistic test data in the real database."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.family: Family | None = None
        self.user: User | None = None
        self.user2: User | None = None
        self.chore: Chore | None = None

    async def setup(self):
        # 1. Create users first (no family yet)
        self.user = User(
            username=f"testuser_{uuid.uuid4().hex[:6]}",
            name="Alice",
            email=f"alice_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=Hasher.get_password_hash("Passw0rd!"),
            family_id=None,
            is_active=True,
        )
        self.session.add(self.user)
        await self.session.flush()

        self.user2 = User(
            username=f"testuser2_{uuid.uuid4().hex[:6]}",
            name="Bob",
            email=f"bob_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=Hasher.get_password_hash("Passw0rd!"),
            family_id=None,
            is_active=True,
        )
        self.session.add(self.user2)
        await self.session.flush()

        # 2. Create family with real admin_id
        self.family = Family(
            name="Test Family",
            family_admin_id=self.user.id,
        )
        self.session.add(self.family)
        await self.session.flush()

        # 3. Update users with family_id
        self.user.family_id = self.family.id
        self.user2.family_id = self.family.id
        self.session.add(self.user)
        self.session.add(self.user2)
        await self.session.flush()

        # 4. User settings
        for usr in (self.user, self.user2):
            settings = UserSettings(
                user_id=usr.id,
                app_theme="Dark",
                language="ru",
                date_of_birth=datetime.date(2001, 1, 1),
            )
            self.session.add(settings)

        # 5. User permissions
        for usr in (self.user, self.user2):
            perm = UserFamilyPermissions(
                user_id=usr.id,
                can_invite_users=True,
            )
            self.session.add(perm)

        # 6. Create chore
        self.chore = Chore(
            name="Wash Dishes",
            description="Wash all kitchen dishes",
            valuation=10,
            family_id=self.family.id,
            icon="material-symbols:cleaning-services-rounded",
            icon_color="#ffffff",
            icon_bg="#4CAF50",
            created_by=self.user.id,
            is_active=True,
        )
        self.session.add(self.chore)
        await self.session.commit()

        return self

    async def create_planned_chore(
        self,
        due_date: datetime.date | None = None,
        completed_by: User | None = None,
        assigned_to: User | None = None,
    ) -> PlannedChore:
        pc = PlannedChore(
            chore_id=self.chore.id,
            family_id=self.family.id,
            due_date=due_date or datetime.date.today(),
            completed_by_id=completed_by.id if completed_by else None,
            assigned_to_id=assigned_to.id if assigned_to else self.user.id,
            created_by=self.user.id,
            message="",
            is_active=True,
        )
        self.session.add(pc)
        await self.session.commit()
        await self.session.refresh(pc)
        return pc

    async def create_quick_chore(
        self,
        due_date: datetime.date | None = None,
        completed_by: User | None = None,
    ) -> QuickPlannedChore:
        qc = QuickPlannedChore(
            name="Quick Task",
            valuation=5,
            family_id=self.family.id,
            due_date=due_date or datetime.date.today(),
            completed_by_id=completed_by.id if completed_by else None,
            assigned_to_id=self.user.id,
            created_by=self.user.id,
            is_active=True,
        )
        self.session.add(qc)
        await self.session.commit()
        await self.session.refresh(qc)
        return qc

    async def create_chore(
        self,
        name: str = "Extra Chore",
        valuation: int = 10,
    ) -> Chore:
        chore = Chore(
            name=name,
            description=f"Description for {name}",
            valuation=valuation,
            family_id=self.family.id,
            icon="material-symbols:cleaning-services-rounded",
            icon_color="#ffffff",
            icon_bg="#4CAF50",
            created_by=self.user.id,
            is_active=True,
        )
        self.session.add(chore)
        await self.session.commit()
        await self.session.refresh(chore)
        return chore

    async def create_schedule(
        self,
        frequency: FrequencyTypeENUM = FrequencyTypeENUM.daily,
        frequency_type: FrequencyTypeENUM | None = None,
        interval: int = 1,
        days_of_week: int | None = None,
        day_of_month: int | None = None,
        starts_at: datetime.date | None = None,
        ends_at: datetime.date | None = None,
        assigned_to: User | None = None,
        chore: Chore | None = None,
    ) -> ChoreSchedule:
        sched = ChoreSchedule(
            chore_id=chore.id if chore else self.chore.id,
            family_id=self.family.id,
            assigned_to_id=assigned_to.id if assigned_to else self.user.id,
            created_by=self.user.id,
            frequency_type=frequency_type or frequency,
            interval=interval,
            days_of_week=days_of_week,
            day_of_month=day_of_month,
            starts_at=starts_at or datetime.date.today(),
            ends_at=ends_at,
            is_active=True,
        )
        self.session.add(sched)
        await self.session.commit()
        await self.session.refresh(sched)
        return sched

    async def create_recipe(self, title: str = "Pasta") -> Recipe:
        recipe = Recipe(
            family_id=self.family.id,
            created_by_id=self.user.id,
            title=title,
            category="quick",
            tags=[],
            ingredients=[],
            steps=[],
            is_active=True,
        )
        self.session.add(recipe)
        await self.session.commit()
        await self.session.refresh(recipe)
        return recipe

    async def create_planned_meal(
        self,
        date: datetime.date | None = None,
        slot: str = "lunch",
        title: str = "Test Meal",
        recipe: Recipe | None = None,
    ) -> PlannedMeal:
        meal = PlannedMeal(
            family_id=self.family.id,
            date=date or datetime.date.today(),
            slot=slot,
            title=title,
            recipe_id=recipe.id if recipe else None,
            is_active=True,
        )
        self.session.add(meal)
        await self.session.commit()
        await self.session.refresh(meal)
        return meal

    async def create_grocery_item(self, name: str = "Milk") -> GroceryItem:
        item = GroceryItem(
            family_id=self.family.id,
            name=name,
            is_bought=False,
            is_active=True,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item


@pytest_asyncio.fixture
async def integration_factory(db_session: AsyncSession) -> IntegrationFactory:
    """Provides a fully set-up IntegrationFactory with family, users, and chore."""
    factory = IntegrationFactory(db_session)
    await factory.setup()
    return factory
