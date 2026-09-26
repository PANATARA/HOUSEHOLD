import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.schemas import GoogleAuthSchema
from auth.services import InvalidGoogleTokenError, verify_google_id_token
from users.models import User
from users.repository import UserRepository

# ==========================================
# Schema Tests
# ==========================================


def test_google_auth_schema_with_credential():
    schema = GoogleAuthSchema(credential="valid_jwt_credential")
    assert schema.get_token() == "valid_jwt_credential"


def test_google_auth_schema_with_token():
    schema = GoogleAuthSchema(token="valid_jwt_token")
    assert schema.get_token() == "valid_jwt_token"


def test_google_auth_schema_empty():
    schema = GoogleAuthSchema()
    with pytest.raises(ValueError):
        schema.get_token()


# ==========================================
# Service Tests
# ==========================================


@pytest.mark.asyncio
async def test_verify_google_id_token_success():
    mock_payload = {
        "sub": "1234567890",
        "email": "test@gmail.com",
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "iss": "https://accounts.google.com",
    }
    with patch(
        "auth.services.google_id_token.verify_oauth2_token", return_value=mock_payload
    ):
        result = await verify_google_id_token("mock_google_jwt")
        assert result["sub"] == "1234567890"
        assert result["email"] == "test@gmail.com"


@pytest.mark.asyncio
async def test_verify_google_id_token_invalid_issuer():
    mock_payload = {
        "sub": "1234567890",
        "email": "test@gmail.com",
        "iss": "https://malicious-issuer.com",
    }
    with patch(
        "auth.services.google_id_token.verify_oauth2_token", return_value=mock_payload
    ):
        with pytest.raises(InvalidGoogleTokenError, match="Invalid token issuer"):
            await verify_google_id_token("mock_google_jwt")


@pytest.mark.asyncio
async def test_verify_google_id_token_invalid():
    with patch(
        "auth.services.google_id_token.verify_oauth2_token",
        side_effect=ValueError("Token expired"),
    ):
        with pytest.raises(InvalidGoogleTokenError):
            await verify_google_id_token("mock_google_jwt")


# ==========================================
# Repository Upsert Tests
# ==========================================


@pytest.mark.asyncio
async def test_upsert_google_user_new(mock_db_session: AsyncMock):
    repo = UserRepository(mock_db_session)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result

    user, is_new = await repo.upsert_google_user(
        sub="sub_12345",
        email="newuser@gmail.com",
        name="John",
    )

    assert is_new is True
    assert user.email == "newuser@gmail.com"
    assert user.google_sub == "sub_12345"
    assert user.name == "John"
    assert mock_db_session.add.call_count == 2  # user + settings


@pytest.mark.asyncio
async def test_upsert_google_user_existing(mock_db_session: AsyncMock):
    repo = UserRepository(mock_db_session)
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@gmail.com",
        username="existing_user",
        name=None,
        google_sub=None,
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_user
    mock_db_session.execute.return_value = mock_result

    user, is_new = await repo.upsert_google_user(
        sub="sub_99999",
        email="existing@gmail.com",
        name="Jane",
    )

    assert is_new is False
    assert user.google_sub == "sub_99999"
    assert user.name == "Jane"


# ==========================================
# API Endpoint Tests
# ==========================================


@pytest.mark.asyncio
async def test_api_google_auth_success(
    async_client, mock_db_session: AsyncMock, sample_user: User
):
    mock_payload = {
        "sub": "google_sub_12345",
        "email": "user@gmail.com",
        "email_verified": True,
        "name": "Google User",
        "given_name": "Google",
        "family_name": "User",
        "iss": "https://accounts.google.com",
    }

    with (
        patch(
            "auth.router.verify_google_id_token", AsyncMock(return_value=mock_payload)
        ),
        patch.object(
            UserRepository,
            "upsert_google_user",
            AsyncMock(return_value=(sample_user, True)),
        ),
    ):
        resp = await async_client.post(
            "/api/auth/google",
            json={"credential": "sample_valid_google_jwt"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["is_new_user"] is True


@pytest.mark.asyncio
async def test_api_google_auth_invalid_token(async_client, mock_db_session: AsyncMock):
    with patch(
        "auth.router.verify_google_id_token",
        AsyncMock(side_effect=InvalidGoogleTokenError("Expired")),
    ):
        resp = await async_client.post(
            "/api/auth/google",
            json={"credential": "invalid_token"},
        )
        assert resp.status_code == 401
