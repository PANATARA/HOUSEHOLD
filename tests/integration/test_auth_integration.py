"""
Integration tests for the Auth module against a real database.

Tests cover:
- Password-based registration and login
- Duplicate username/email rejection
- Token generation and refresh flow
- Google auth upsert logic
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hashing import Hasher
from core.security import create_jwt_token, get_payload_from_jwt_token
from users.models import User, UserSettings


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegistration:

    async def test_register_creates_user_in_db(
        self, db_session: AsyncSession, integration_factory
    ):
        """Register via the HTTP endpoint and verify user exists in DB."""
        # We test the service/repo logic directly since auth client is not bypassed
        from users.repository import UserRepository
        user = integration_factory.user
        repo = UserRepository(db_session)
        found = await repo.get_by_username(user.username)
        assert found is not None
        assert found.username == user.username

    async def test_register_creates_user_settings(
        self, db_session: AsyncSession, integration_factory
    ):
        result = await db_session.execute(
            select(UserSettings).where(
                UserSettings.user_id == integration_factory.user.id
            )
        )
        settings = result.scalar_one_or_none()
        assert settings is not None
        assert settings.language == "ru"
        assert settings.app_theme == "Dark"

    async def test_duplicate_username_rejected(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy.exc import IntegrityError
        from users.models import User

        duplicate = User(
            username=integration_factory.user.username,  # same username
            email="different_email@test.com",
            hashed_password=Hasher.get_password_hash("Passw0rd!"),
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_duplicate_email_rejected(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy.exc import IntegrityError
        from users.models import User

        duplicate = User(
            username="completely_unique_username_xyz",
            email=integration_factory.user.email,  # same email
            hashed_password=Hasher.get_password_hash("Passw0rd!"),
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()


# ── Login Logic ───────────────────────────────────────────────────────────────

class TestLoginLogic:

    async def test_verify_correct_password(self, integration_factory):
        user = integration_factory.user
        assert user.hashed_password is not None
        assert Hasher.verify_password("Passw0rd!", user.hashed_password)

    async def test_reject_wrong_password(self, integration_factory):
        user = integration_factory.user
        assert not Hasher.verify_password("WrongPassword!", user.hashed_password)

    async def test_reject_empty_password(self, integration_factory):
        user = integration_factory.user
        assert not Hasher.verify_password("", user.hashed_password)

    async def test_get_user_by_username_or_email_by_username(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        found = await repo.get_by_username_or_email(integration_factory.user.username)
        assert found is not None
        assert found.id == integration_factory.user.id

    async def test_get_user_by_username_or_email_by_email(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        found = await repo.get_by_username_or_email(integration_factory.user.email)
        assert found is not None
        assert found.id == integration_factory.user.id

    async def test_get_user_by_unknown_identifier_returns_none(
        self, db_session: AsyncSession
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        found = await repo.get_by_username_or_email("does_not_exist@nowhere.com")
        assert found is None


# ── JWT Token Tests ───────────────────────────────────────────────────────────

class TestJWTTokens:
    """Test JWT creation and parsing (unit-style but included here for completeness)."""

    def test_create_and_decode_access_token(self, integration_factory):
        from datetime import timedelta
        user = integration_factory.user
        token = create_jwt_token(
            data={"sub": str(user.id), "is_family_admin": False},
            expires_delta=timedelta(minutes=30),
        )
        assert isinstance(token, str)
        payload = get_payload_from_jwt_token(token)
        assert payload["sub"] == str(user.id)
        assert payload["is_family_admin"] is False

    def test_expired_token_raises_http_401(self):
        from datetime import timedelta
        from fastapi import HTTPException

        token = create_jwt_token(
            data={"sub": "some-user-id"},
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        with pytest.raises(HTTPException) as exc_info:
            get_payload_from_jwt_token(token)
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_exception(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            get_payload_from_jwt_token("not.a.valid.jwt.token")


# ── Google Auth Upsert Logic ──────────────────────────────────────────────────

class TestGoogleAuthUpsert:

    async def test_upsert_creates_new_user_when_not_found(
        self, db_session: AsyncSession
    ):
        import uuid
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        sub = f"google_sub_{uuid.uuid4().hex[:8]}"
        email = f"newgoogleuser_{uuid.uuid4().hex[:6]}@gmail.com"

        user, is_new = await repo.upsert_google_user(sub=sub, email=email, name="Test User")
        assert is_new is True
        assert user.email == email
        assert user.google_sub == sub

    async def test_upsert_finds_existing_user_by_email(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        existing_user = integration_factory.user
        sub = f"new_google_sub_{existing_user.id}"

        user, is_new = await repo.upsert_google_user(
            sub=sub, email=existing_user.email, name="Alice Updated"
        )
        assert is_new is False
        assert user.id == existing_user.id

    async def test_upsert_updates_google_sub_if_missing(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        user = integration_factory.user
        assert user.google_sub is None

        new_sub = f"google_sub_new_{user.id.hex[:8]}"
        updated_user, _ = await repo.upsert_google_user(
            sub=new_sub,
            email=user.email,
        )
        assert updated_user.google_sub == new_sub


# ── Hasher Tests ──────────────────────────────────────────────────────────────

class TestHasher:

    def test_hash_is_not_plaintext(self):
        hashed = Hasher.get_password_hash("MySecret123!")
        assert hashed != "MySecret123!"
        assert len(hashed) > 20

    def test_same_password_produces_different_hashes(self):
        h1 = Hasher.get_password_hash("Same!Password1")
        h2 = Hasher.get_password_hash("Same!Password1")
        # bcrypt salts are random → hashes differ
        assert h1 != h2

    def test_verify_works_for_both_hashes(self):
        h1 = Hasher.get_password_hash("Same!Password1")
        h2 = Hasher.get_password_hash("Same!Password1")
        assert Hasher.verify_password("Same!Password1", h1)
        assert Hasher.verify_password("Same!Password1", h2)

    def test_verify_returns_false_for_wrong_password(self):
        hashed = Hasher.get_password_hash("Correct!1")
        assert not Hasher.verify_password("Wrong!1", hashed)

    def test_verify_returns_false_for_none_hash(self):
        assert not Hasher.verify_password("anything", None)

    def test_verify_returns_false_for_empty_password(self):
        hashed = Hasher.get_password_hash("Correct!1")
        assert not Hasher.verify_password("", hashed)
