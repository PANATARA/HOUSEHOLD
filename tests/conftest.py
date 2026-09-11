import datetime
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from core.enums import FrequencyTypeENUM
from families.models import Family
from users.models import User
from chores.models import Chore
from planned_chores.models import ChoreSchedule, PlannedChore
from database_connection import get_db
from core.permissions import ChoreSchedulePermission, PlannedChorePermission, FamilyMemberPermission
from main import app


@pytest.fixture
def sample_family_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_family(sample_family_id: uuid.UUID) -> Family:
    return Family(
        id=sample_family_id,
        name="Test Family",
        is_active=True,
    )


@pytest.fixture
def sample_user(sample_user_id: uuid.UUID, sample_family_id: uuid.UUID) -> User:
    return User(
        id=sample_user_id,
        username="testuser",
        name="Test",
        surname="User",
        email="test@example.com",
        family_id=sample_family_id,
        is_superuser=False,
        is_active=True,
    )


@pytest.fixture
def sample_chore(sample_family_id: uuid.UUID, sample_user_id: uuid.UUID) -> Chore:
    return Chore(
        id=uuid.uuid4(),
        name="Wash dishes",
        description="Wash all kitchen dishes",
        valuation=10,
        family_id=sample_family_id,
        icon="material-symbols:cleaning-services-rounded",
        icon_color="#ffffff",
        icon_bg="#4CAF50",
        created_by=sample_user_id,
        is_active=True,
    )


@pytest.fixture
def sample_schedule(
    sample_chore: Chore, sample_user: User, sample_family_id: uuid.UUID
) -> ChoreSchedule:
    return ChoreSchedule(
        id=uuid.uuid4(),
        chore_id=sample_chore.id,
        family_id=sample_family_id,
        assigned_to_id=sample_user.id,
        created_by=sample_user.id,
        frequency_type=FrequencyTypeENUM.daily,
        interval=1,
        days_of_week=None,
        day_of_month=None,
        starts_at=datetime.date.today(),
        ends_at=None,
        last_generated_until=None,
        is_active=True,
    )


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Provides a fully functional AsyncMock for SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    # Default execute result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_scalars.first.return_value = None
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = None

    mock_mappings = MagicMock()
    mock_mappings.all.return_value = []
    mock_mappings.first.return_value = None
    mock_result.mappings.return_value = mock_mappings

    session.execute.return_value = mock_result

    # context manager support: async with session.begin():
    transaction_mock = AsyncMock()
    transaction_mock.__aenter__.return_value = session
    transaction_mock.__aexit__.return_value = None
    session.begin = MagicMock(return_value=transaction_mock)
    session.begin_nested = MagicMock(return_value=transaction_mock)

    return session


@pytest.fixture
async def async_client(
    sample_user: User, mock_db_session: AsyncMock
) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI AsyncClient with mocked database session and auth permissions.
    Ensures tests run in complete isolation from production DB and network.
    """
    from fastapi import Request
    from core.permissions import BasePermission

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    async def mock_permission_call(self, request: Request):
        return sample_user

    transport = ASGITransport(app=app)
    with patch.object(BasePermission, "__call__", mock_permission_call):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()
