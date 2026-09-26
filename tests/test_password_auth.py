import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from core.hashing import Hasher
from database_connection import get_db
from main import app
from users.models import User
from users.repository import UserRepository

# ==========================================
# Unit Tests for Hasher
# ==========================================


def test_hasher_hash_and_verify():
    password = "supersecretpassword123"
    hashed = Hasher.get_password_hash(password)
    assert hashed != password
    assert Hasher.verify_password(password, hashed) is True
    assert Hasher.verify_password("wrongpassword", hashed) is False
    assert Hasher.verify_password("", hashed) is False
    assert Hasher.verify_password(password, None) is False


# ==========================================
# Repository Tests
# ==========================================


@pytest.mark.asyncio
async def test_create_user_with_password(mock_db_session: AsyncMock):
    repo = UserRepository(mock_db_session)
    hashed = Hasher.get_password_hash("password123")
    user = await repo.create_user_with_password(
        username="john_doe",
        hashed_password=hashed,
        name="John",
    )

    assert user.username == "john_doe"
    assert user.name == "John"
    assert user.hashed_password == hashed
    assert mock_db_session.add.call_count == 2  # user + settings


# ==========================================
# API Endpoint Tests
# ==========================================


@pytest.mark.asyncio
async def test_register_success(mock_db_session: AsyncMock):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/register",
            json={
                "username": "new_user",
                "password": "secretpassword",
                "name": "New User",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["is_new_user"] is True


@pytest.mark.asyncio
async def test_register_duplicate_username(mock_db_session: AsyncMock):
    existing_user = User(
        id=uuid.uuid4(),
        username="existing_user",
        hashed_password="some_hash",
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_user
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/register",
            json={
                "username": "existing_user",
                "password": "secretpassword",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "уже существует" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_validation_short_password(mock_db_session: AsyncMock):
    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/register",
            json={
                "username": "user123",
                "password": "123",  # min length 6
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(mock_db_session: AsyncMock):
    hashed = Hasher.get_password_hash("mypassword")
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        hashed_password=hashed,
        is_active=True,
        family_id=None,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "mypassword"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["is_new_user"] is False


@pytest.mark.asyncio
async def test_login_wrong_password(mock_db_session: AsyncMock):
    hashed = Hasher.get_password_hash("correct_password")
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        hashed_password=hashed,
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrong_password"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "Неверный логин или пароль" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(mock_db_session: AsyncMock):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "any_password"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "Неверный логин или пароль" in response.json()["detail"]
