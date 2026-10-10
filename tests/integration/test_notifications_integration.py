"""
Integration tests for notifications:
- DeviceRepository (real PostgreSQL operations)
- NotificationService (multicast dispatch, token pruning, fallback when FCM not configured)
- Notification API endpoints (/api/notifications/devices, /api/notifications/test)
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.models import UserDevice
from notifications.repository import DeviceRepository
from notifications.service import NotificationService, notify_family_about_new_chore
from users.models import User


# ─── DeviceRepository Integration Tests ──────────────────────────────────────────


class TestDeviceRepository:
    """Tests for DeviceRepository with real PostgreSQL queries."""

    async def test_register_new_device(self, db_session: AsyncSession, integration_factory):
        repo = DeviceRepository(db_session)
        token = f"fcm_token_{uuid.uuid4().hex}"

        device = await repo.register_device(
            user_id=integration_factory.user.id,
            token=token,
            device_type="android",
            device_name="Pixel 8",
        )

        assert device.id is not None
        assert device.user_id == integration_factory.user.id
        assert device.token == token
        assert device.device_type == "android"
        assert device.device_name == "Pixel 8"

        # Verify persisted in DB
        result = await db_session.execute(select(UserDevice).where(UserDevice.token == token))
        persisted = result.scalar_one()
        assert persisted.id == device.id

    async def test_register_device_updates_existing_token(
        self, db_session: AsyncSession, integration_factory
    ):
        """Registering an existing token with a new user/device_name updates the record."""
        repo = DeviceRepository(db_session)
        token = f"shared_token_{uuid.uuid4().hex}"

        # Register for user 1
        d1 = await repo.register_device(
            user_id=integration_factory.user.id,
            token=token,
            device_type="android",
            device_name="Old Phone",
        )

        # Register same token for user 2
        d2 = await repo.register_device(
            user_id=integration_factory.user2.id,
            token=token,
            device_type="ios",
            device_name="New Phone",
        )

        assert d1.id == d2.id
        assert d2.user_id == integration_factory.user2.id
        assert d2.device_type == "ios"
        assert d2.device_name == "New Phone"

    async def test_unregister_device_success(self, db_session: AsyncSession, integration_factory):
        repo = DeviceRepository(db_session)
        token = f"token_del_{uuid.uuid4().hex}"

        await repo.register_device(
            user_id=integration_factory.user.id,
            token=token,
        )

        deleted = await repo.unregister_device(
            user_id=integration_factory.user.id,
            token=token,
        )
        assert deleted is True

        # Verify not in DB
        result = await db_session.execute(select(UserDevice).where(UserDevice.token == token))
        assert result.scalar_one_or_none() is None

    async def test_unregister_device_non_existent_returns_false(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        deleted = await repo.unregister_device(
            user_id=integration_factory.user.id,
            token="non_existent_token_123",
        )
        assert deleted is False

    async def test_unregister_device_different_user_returns_false(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        token = f"token_owner_{uuid.uuid4().hex}"

        await repo.register_device(
            user_id=integration_factory.user.id,
            token=token,
        )

        # User2 tries to unregister User1's token
        deleted = await repo.unregister_device(
            user_id=integration_factory.user2.id,
            token=token,
        )
        assert deleted is False

    async def test_get_user_devices_returns_all_for_user(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        t1 = f"tok1_{uuid.uuid4().hex}"
        t2 = f"tok2_{uuid.uuid4().hex}"

        await repo.register_device(user_id=integration_factory.user.id, token=t1)
        await repo.register_device(user_id=integration_factory.user.id, token=t2)

        devices = await repo.get_user_devices(integration_factory.user.id)
        tokens = [d.token for d in devices]
        assert t1 in tokens
        assert t2 in tokens

    async def test_get_user_tokens_filters_by_android(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        android_tok = f"android_{uuid.uuid4().hex}"
        ios_tok = f"ios_{uuid.uuid4().hex}"

        await repo.register_device(
            user_id=integration_factory.user.id,
            token=android_tok,
            device_type="android",
        )
        await repo.register_device(
            user_id=integration_factory.user.id,
            token=ios_tok,
            device_type="ios",
        )

        tokens = await repo.get_user_tokens(integration_factory.user.id)
        assert android_tok in tokens
        assert ios_tok not in tokens

    async def test_get_family_tokens_aggregates_across_members(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        tok_u1 = f"u1_{uuid.uuid4().hex}"
        tok_u2 = f"u2_{uuid.uuid4().hex}"

        await repo.register_device(
            user_id=integration_factory.user.id,
            token=tok_u1,
            device_type="android",
        )
        await repo.register_device(
            user_id=integration_factory.user2.id,
            token=tok_u2,
            device_type="android",
        )

        family_tokens = await repo.get_family_tokens(integration_factory.family.id)
        assert tok_u1 in family_tokens
        assert tok_u2 in family_tokens

    async def test_get_family_tokens_exclude_initiator(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        tok_u1 = f"u1_{uuid.uuid4().hex}"
        tok_u2 = f"u2_{uuid.uuid4().hex}"

        await repo.register_device(
            user_id=integration_factory.user.id,
            token=tok_u1,
            device_type="android",
        )
        await repo.register_device(
            user_id=integration_factory.user2.id,
            token=tok_u2,
            device_type="android",
        )

        family_tokens = await repo.get_family_tokens(
            family_id=integration_factory.family.id,
            exclude_user_id=integration_factory.user.id,
        )
        assert tok_u1 not in family_tokens
        assert tok_u2 in family_tokens

    async def test_delete_tokens_removes_batch(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        t1 = f"del1_{uuid.uuid4().hex}"
        t2 = f"del2_{uuid.uuid4().hex}"
        t3 = f"keep_{uuid.uuid4().hex}"

        await repo.register_device(user_id=integration_factory.user.id, token=t1)
        await repo.register_device(user_id=integration_factory.user.id, token=t2)
        await repo.register_device(user_id=integration_factory.user.id, token=t3)

        await repo.delete_tokens([t1, t2])

        remaining = await repo.get_user_tokens(integration_factory.user.id)
        assert t1 not in remaining
        assert t2 not in remaining
        assert t3 in remaining

    async def test_delete_tokens_empty_list_is_noop(
        self, db_session: AsyncSession
    ):
        repo = DeviceRepository(db_session)
        # Should not raise any error
        await repo.delete_tokens([])


# ─── NotificationService Integration Tests ────────────────────────────────────────


class TestNotificationService:
    """Tests for NotificationService logic and error handling."""

    async def test_send_multicast_empty_tokens_returns_zero(self, db_session: AsyncSession):
        svc = NotificationService(db_session)
        res = await svc.send_multicast([], "Title", "Body")
        assert res == {"total": 0, "success": 0, "failure": 0, "pruned": 0}

    async def test_send_multicast_fcm_not_available_returns_graceful_dict(
        self, db_session: AsyncSession
    ):
        with patch("notifications.service.is_fcm_available", return_value=False):
            svc = NotificationService(db_session)
            res = await svc.send_multicast(["fake_token_1", "fake_token_2"], "Title", "Body")
            assert res["total"] == 2
            assert res["success"] == 0
            assert res["failure"] == 2
            assert res["reason"] == "fcm_not_configured"

    async def test_send_multicast_successful_batch_send(
        self, db_session: AsyncSession, integration_factory
    ):
        mock_response = MagicMock()
        mock_response.success_count = 2
        mock_response.failure_count = 0
        mock_response.responses = []

        with (
            patch("notifications.service.is_fcm_available", return_value=True),
            patch("firebase_admin.messaging.send_each_for_multicast", return_value=mock_response),
        ):
            svc = NotificationService(db_session)
            tokens = ["tok_1", "tok_2"]
            res = await svc.send_multicast(tokens, "Hello", "World", {"key": "val"})

            assert res["total"] == 2
            assert res["success"] == 2
            assert res["failure"] == 0
            assert res["pruned"] == 0

    async def test_send_multicast_prunes_invalid_tokens(
        self, db_session: AsyncSession, integration_factory
    ):
        """Tokens reported invalid by FCM must be automatically deleted from DB."""
        repo = DeviceRepository(db_session)
        bad_token = f"bad_token_{uuid.uuid4().hex}"
        await repo.register_device(user_id=integration_factory.user.id, token=bad_token)

        from firebase_admin import messaging

        mock_err_resp = MagicMock()
        mock_err_resp.success = False
        mock_err_resp.exception = messaging.UnregisteredError("Requested entity was not found.")

        mock_batch_resp = MagicMock()
        mock_batch_resp.success_count = 0
        mock_batch_resp.failure_count = 1
        mock_batch_resp.responses = [mock_err_resp]

        with (
            patch("notifications.service.is_fcm_available", return_value=True),
            patch("firebase_admin.messaging.send_each_for_multicast", return_value=mock_batch_resp),
        ):
            svc = NotificationService(db_session)
            res = await svc.send_multicast([bad_token], "Title", "Body")

            assert res["failure"] == 1
            assert res["pruned"] == 1

            # Assert token was pruned from database
            devices = await repo.get_user_tokens(integration_factory.user.id)
            assert bad_token not in devices

    async def test_send_to_user_gathers_user_tokens(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = DeviceRepository(db_session)
        token = f"user_tok_{uuid.uuid4().hex}"
        await repo.register_device(user_id=integration_factory.user.id, token=token)

        svc = NotificationService(db_session)
        with patch.object(svc, "send_multicast") as mock_multicast:
            mock_multicast.return_value = {"total": 1, "success": 1}
            await svc.send_to_user(
                user_id=integration_factory.user.id,
                title="Personal Note",
                body="You got this!",
            )
            mock_multicast.assert_called_once()
            call_tokens = mock_multicast.call_args[0][0]
            assert token in call_tokens

    async def test_notify_family_new_chore_constructs_proper_payload(
        self, db_session: AsyncSession, integration_factory
    ):
        svc = NotificationService(db_session)
        with patch.object(svc, "send_to_family") as mock_send:
            mock_send.return_value = {"total": 1, "success": 1}

            chore_id = uuid.uuid4()
            await svc.notify_family_new_chore(
                family_id=integration_factory.family.id,
                creator_id=integration_factory.user.id,
                creator_name="Alice",
                chore_name="Wash Dishes",
                chore_id=chore_id,
            )

            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert kwargs["family_id"] == integration_factory.family.id
            assert kwargs["exclude_user_id"] == integration_factory.user.id
            assert "Wash Dishes" in kwargs["title"]
            assert kwargs["data"]["chore_name"] == "Wash Dishes"
            assert kwargs["data"]["chore_id"] == str(chore_id)

    async def test_notify_family_about_new_chore_background_task(
        self, db_session: AsyncSession, integration_factory
    ):
        """Tests the background task function notify_family_about_new_chore handles no family gracefully."""
        # When family_id is None, it should return immediately without opening session
        await notify_family_about_new_chore(
            family_id=None,
            creator_id=integration_factory.user.id,
            creator_name="Bob",
            chore_name="Clean Room",
            chore_id=uuid.uuid4(),
        )


# ─── Notifications API Endpoints ───────────────────────────────────────────────


class TestNotificationEndpoints:
    """Integration tests for notification endpoints via ASGI client."""

    async def test_register_device_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        token = f"api_token_{uuid.uuid4().hex}"
        payload = {
            "token": token,
            "device_type": "android",
            "device_name": "Galaxy S24",
        }
        resp = await integration_client.post("/api/notifications/devices", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["token"] == token
        assert data["device_name"] == "Galaxy S24"

    async def test_list_user_devices_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        token = f"list_tok_{uuid.uuid4().hex}"
        payload = {"token": token, "device_type": "android"}
        await integration_client.post("/api/notifications/devices", json=payload)

        resp = await integration_client.get("/api/notifications/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(d["token"] == token for d in data)

    async def test_unregister_device_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        token = f"unreg_tok_{uuid.uuid4().hex}"
        payload = {"token": token, "device_type": "android"}
        await integration_client.post("/api/notifications/devices", json=payload)

        del_resp = await integration_client.delete(f"/api/notifications/devices/{token}")
        assert del_resp.status_code == 204

        # Confirm it's gone
        list_resp = await integration_client.get("/api/notifications/devices")
        tokens = [d["token"] for d in list_resp.json()]
        assert token not in tokens

    async def test_send_test_notification_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "title": "Test Title",
            "body": "Test Body message",
            "data": {"foo": "bar"},
        }
        resp = await integration_client.post("/api/notifications/test", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "fcm_available" in data
        assert "delivery" in data
