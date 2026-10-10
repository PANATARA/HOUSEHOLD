"""
Integration tests for Users & Families API endpoints and membership lifecycle services:
- Users endpoints (/api/users/me/profile, /api/users/me/settings, /api/users/{user_id})
- Families endpoints (/api/families/, /api/families/members, /api/families/events)
- Membership services: LogoutUserFromFamilyService, GenerateFamilyInviteTokenService, JoinFamilyByInviteCodeService
"""

import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.families import InvalidInviteCodeError, UserCannotLeaveFamily
from core.hashing import Hasher
from families.models import Event, Family
from families.repository import EventRepository, FamilyRepository
from families.services import (
    GenerateFamilyInviteTokenService,
    JoinFamilyByInviteCodeService,
    LogoutUserFromFamilyService,
)
from users.models import User, UserFamilyPermissions, UserSettings
from users.repository import UserPermissionsRepository, UserRepository


# ─── Users API Endpoints ────────────────────────────────────────────────────────


class TestUsersApiEndpoints:
    """Integration tests for /api/users routes against real database."""

    async def test_me_get_user_profile(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/users/me/profile")
        assert resp.status_code == 200
        data = resp.json()

        assert data["id"] == str(integration_factory.user.id)
        assert data["username"] == integration_factory.user.username
        assert data["name"] == "Alice"
        assert data["is_family_member"] is True
        assert data["is_family_admin"] is True
        assert "level" in data
        assert "exp_to_next_total" in data
        assert "progress_percent" in data
        assert "week_completed" in data
        assert "month_completed" in data

    async def test_me_user_partial_update(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        db_session.expunge(integration_factory.user)
        payload = {
            "name": "Alice Wonderland",
            "icon": "solar:smile-bold",
            "icon_bg": "#FF5722",
            "icon_color": "#FFFFFF",
        }
        resp = await integration_client.patch("/api/users/me/profile", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["name"] == "Alice Wonderland"
        assert data["icon"] == "solar:smile-bold"
        assert data["icon_bg"] == "#FF5722"

        # Verify DB updated
        result = await db_session.execute(
            select(User).where(User.id == integration_factory.user.id)
        )
        db_user = result.scalar_one()
        assert db_user.name == "Alice Wonderland"

    async def test_me_user_get_settings(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/users/me/settings")
        assert resp.status_code == 200
        data = resp.json()

        assert data["app_theme"] == "Dark"
        assert data["language"] == "ru"
        assert data["date_of_birth"] == "2001-01-01"

    async def test_me_user_settings_partial_update(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        payload = {
            "app_theme": "Light",
            "language": "en",
        }
        resp = await integration_client.patch("/api/users/me/settings", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["app_theme"] == "Light"
        assert data["language"] == "en"

        # Verify in DB
        result = await db_session.execute(
            select(UserSettings).where(UserSettings.user_id == integration_factory.user.id)
        )
        db_settings = result.scalar_one()
        assert db_settings.app_theme == "Light"
        assert db_settings.language == "en"

    async def test_get_user_profile_by_id_in_same_family(
        self, integration_client: AsyncClient, integration_factory
    ):
        target_id = integration_factory.user2.id
        resp = await integration_client.get(f"/api/users/{target_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["id"] == str(target_id)
        assert data["username"] == integration_factory.user2.username
        assert data["name"] == "Bob"
        assert data["is_family_member"] is True
        assert data["is_family_admin"] is False


# ─── Families API Endpoints ─────────────────────────────────────────────────────


class TestFamiliesApiEndpoints:
    """Integration tests for /api/families routes against real database."""

    async def test_update_family_profile(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        payload = {
            "name": "Updated Family Name",
            "icon": "solar:home-bold",
            "icon_color": "#2196F3",
            "icon_bg": "#E3F2FD",
        }
        db_session.expunge(integration_factory.family)
        resp = await integration_client.patch("/api/families/", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["name"] == "Updated Family Name"
        assert data["icon"] == "solar:home-bold"

    async def test_get_family_members(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/families/members")
        assert resp.status_code == 200
        data = resp.json()

        members = data.get("members", data)
        assert isinstance(members, list)
        member_ids = [m["id"] for m in members]
        assert str(integration_factory.user.id) in member_ids
        assert str(integration_factory.user2.id) in member_ids

    async def test_events_crud_lifecycle(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        now = datetime.datetime.now().replace(microsecond=0)
        # 1. Create event
        payload = {
            "name": "Family Dinner",
            "description": "Sunday evening dinner",
            "date": now.isoformat(),
            "icon": "solar:calendar-bold",
            "icon_color": "#FFFFFF",
            "icon_bg": "#FF9800",
        }
        resp = await integration_client.post("/api/families/events", json=payload)
        assert resp.status_code == 200
        event_data = resp.json()
        event_id = event_data["id"]
        assert event_data["name"] == "Family Dinner"

        # 2. List upcoming events
        list_resp = await integration_client.get("/api/families/events/upcoming")
        assert list_resp.status_code == 200
        events_list = list_resp.json()
        assert any(e["id"] == event_id for e in events_list)

        # 3. Update event
        update_payload = {
            "name": "Gala Family Dinner",
            "date": (now + datetime.timedelta(hours=1)).isoformat(),
        }
        update_resp = await integration_client.patch(
            f"/api/families/events/{event_id}",
            json=update_payload,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Gala Family Dinner"

        # 4. Delete event
        del_resp = await integration_client.delete(f"/api/families/events/{event_id}")
        assert del_resp.status_code == 200


# ─── Membership Services ───────────────────────────────────────────────────────


class TestFamilyMembershipServices:
    """Integration tests for family leaving and invite/join flows."""

    async def test_logout_user_from_family_admin_raises_error(
        self, db_session: AsyncSession, integration_factory
    ):
        """Family admin cannot leave the family without transferring ownership."""
        svc = LogoutUserFromFamilyService(
            user=integration_factory.user,
            db_session=db_session,
        )
        with pytest.raises(UserCannotLeaveFamily):
            await svc.run_process()

    async def test_logout_regular_user_clears_family_id_and_permissions(
        self, db_session: AsyncSession, integration_factory
    ):
        """Regular user leaving family has family_id cleared and permissions deleted."""
        user2 = integration_factory.user2
        assert user2.family_id == integration_factory.family.id

        svc = LogoutUserFromFamilyService(
            user=user2,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(user2)
        assert user2.family_id is None

        # Check permissions deleted
        perm_repo = UserPermissionsRepository(db_session)
        perm = await perm_repo.get_by_user_id(user2.id)
        assert perm is None

    async def test_generate_invite_token_and_join_flow(
        self, db_session: AsyncSession, integration_factory
    ):
        """Tests invite code generation and subsequent joining of a new user."""
        redis_store = {}

        class MockRedisPipeline:
            def __init__(self, store):
                self.store = store
                self.commands = []

            def set(self, key, value, ex=None):
                self.commands.append((key, value))

            async def execute(self):
                for k, v in self.commands:
                    self.store[k] = v

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        class MockRedisClient:
            def __init__(self, store):
                self.store = store

            async def get(self, key):
                return self.store.get(key)

            async def ttl(self, key):
                return 300 if key in self.store else -2

            def pipeline(self, transaction=True):
                return MockRedisPipeline(self.store)

        mock_redis = MockRedisClient(redis_store)

        with patch("families.services.redis_client.get_client", AsyncMock(return_value=mock_redis)):
            # 1. Admin generates invite token
            gen_svc = GenerateFamilyInviteTokenService(
                user=integration_factory.user,
                db_session=db_session,
            )
            code, ttl = await gen_svc.run_process()
            assert len(code) == 6
            assert ttl == 300

            # 2. Create a new standalone user (not in any family)
            new_user = User(
                username=f"newbie_{uuid.uuid4().hex[:6]}",
                name="Newbie",
                email=f"newbie_{uuid.uuid4().hex[:6]}@example.com",
                hashed_password=Hasher.get_password_hash("Secret123!"),
                family_id=None,
                is_active=True,
            )
            db_session.add(new_user)
            await db_session.flush()

            # 3. Join family using the invite code
            join_svc = JoinFamilyByInviteCodeService(
                user=new_user,
                invite_code=code,
                db_session=db_session,
            )
            joined_family = await join_svc.run_process()
            assert joined_family.id == integration_factory.family.id

            # Verify new_user is now part of the family in DB
            await db_session.refresh(new_user)
            assert new_user.family_id == integration_factory.family.id

            # Verify permissions created
            perm_repo = UserPermissionsRepository(db_session)
            perm = await perm_repo.get_by_user_id(new_user.id)
            assert perm is not None
            assert perm.can_invite_users is True

    async def test_join_family_invalid_code_raises_error(
        self, db_session: AsyncSession, integration_factory
    ):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("families.services.redis_client.get_client", AsyncMock(return_value=mock_redis)):
            user = User(
                username=f"outsider_{uuid.uuid4().hex[:6]}",
                name="Outsider",
                email=f"outsider_{uuid.uuid4().hex[:6]}@example.com",
                hashed_password=Hasher.get_password_hash("Pass!"),
                family_id=None,
                is_active=True,
            )
            db_session.add(user)
            await db_session.flush()

            svc = JoinFamilyByInviteCodeService(
                user=user,
                invite_code="INVALID",
                db_session=db_session,
            )
            with pytest.raises(InvalidInviteCodeError):
                await svc.run_process()
