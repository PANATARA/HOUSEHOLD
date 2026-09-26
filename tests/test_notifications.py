import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from notifications.models import UserDevice
from notifications.repository import DeviceRepository
from notifications.schemas import (
    DeviceRegisterSchema,
    DeviceResponseSchema,
    NotificationSendTestSchema,
)
from notifications.service import NotificationService
from users.models import User

# ==========================================
# Schema Tests
# ==========================================


def test_device_register_schema_valid():
    schema = DeviceRegisterSchema(
        token="sample_fcm_token_1234567890",
        device_type="android",
        device_name="Pixel 8 Pro",
    )
    assert schema.token == "sample_fcm_token_1234567890"
    assert schema.device_type == "android"
    assert schema.device_name == "Pixel 8 Pro"


def test_device_register_schema_defaults():
    schema = DeviceRegisterSchema(token="sample_fcm_token_1234567890")
    assert schema.device_type == "android"
    assert schema.device_name is None


def test_device_register_schema_invalid_token():
    with pytest.raises(ValidationError):
        DeviceRegisterSchema(token="short")


def test_device_response_schema():
    now = datetime.now()
    device_id = uuid.uuid4()
    user_id = uuid.uuid4()

    device_mock = MagicMock()
    device_mock.id = device_id
    device_mock.user_id = user_id
    device_mock.token = "token_abc_1234567890"
    device_mock.device_type = "android"
    device_mock.device_name = "Samsung Galaxy"
    device_mock.created_at = now
    device_mock.updated_at = now

    schema = DeviceResponseSchema.model_validate(device_mock)
    assert schema.id == device_id
    assert schema.user_id == user_id
    assert schema.token == "token_abc_1234567890"
    assert schema.device_type == "android"
    assert schema.device_name == "Samsung Galaxy"


def test_notification_send_test_schema():
    schema = NotificationSendTestSchema(
        title="Custom title",
        body="Custom body message",
        data={"key": "value"},
    )
    assert schema.title == "Custom title"
    assert schema.body == "Custom body message"
    assert schema.data == {"key": "value"}


# ==========================================
# Repository Tests
# ==========================================


@pytest.mark.asyncio
async def test_device_repository_register_new_device(mock_db_session: AsyncMock):
    repo = DeviceRepository(mock_db_session)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    user_id = uuid.uuid4()
    device = await repo.register_device(
        user_id=user_id,
        token="token_test_123456",
        device_type="android",
        device_name="Test Phone",
    )

    assert mock_db_session.add.called
    assert mock_db_session.flush.called
    assert device.user_id == user_id
    assert device.token == "token_test_123456"


@pytest.mark.asyncio
async def test_device_repository_register_existing_device(mock_db_session: AsyncMock):
    repo = DeviceRepository(mock_db_session)
    existing_device = UserDevice(
        user_id=uuid.uuid4(),
        token="token_existing_123456",
        device_type="android",
        device_name="Old Phone",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_device
    mock_db_session.execute.return_value = mock_result

    new_user_id = uuid.uuid4()
    updated = await repo.register_device(
        user_id=new_user_id,
        token="token_existing_123456",
        device_type="android",
        device_name="New Phone",
    )

    assert updated.user_id == new_user_id
    assert updated.device_name == "New Phone"
    assert mock_db_session.flush.called


@pytest.mark.asyncio
async def test_device_repository_unregister_device(mock_db_session: AsyncMock):
    repo = DeviceRepository(mock_db_session)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = uuid.uuid4()
    mock_db_session.execute.return_value = mock_result

    res = await repo.unregister_device(uuid.uuid4(), "token_123456")
    assert res is True
    assert mock_db_session.flush.called


@pytest.mark.asyncio
async def test_device_repository_get_family_tokens(mock_db_session: AsyncMock):
    repo = DeviceRepository(mock_db_session)
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = ["token_1", "token_2", "token_1"]
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    tokens = await repo.get_family_tokens(
        family_id=uuid.uuid4(),
        exclude_user_id=uuid.uuid4(),
    )
    assert set(tokens) == {"token_1", "token_2"}


@pytest.mark.asyncio
async def test_device_repository_delete_tokens(mock_db_session: AsyncMock):
    repo = DeviceRepository(mock_db_session)
    await repo.delete_tokens(["bad_token_1", "bad_token_2"])
    assert mock_db_session.execute.called
    assert mock_db_session.flush.called


# ==========================================
# Service Tests
# ==========================================


@pytest.mark.asyncio
async def test_notification_service_fcm_not_configured(mock_db_session: AsyncMock):
    with patch("notifications.service.is_fcm_available", return_value=False):
        service = NotificationService(mock_db_session)
        result = await service.send_multicast(
            tokens=["token_1", "token_2"],
            title="Hello",
            body="World",
        )
        assert result["total"] == 2
        assert result["success"] == 0
        assert result["failure"] == 2
        assert result["reason"] == "fcm_not_configured"


@pytest.mark.asyncio
async def test_notification_service_send_multicast_success(mock_db_session: AsyncMock):
    mock_response = MagicMock()
    mock_response.success_count = 2
    mock_response.failure_count = 0
    mock_response.responses = []

    with (
        patch("notifications.service.is_fcm_available", return_value=True),
        patch(
            "notifications.service.messaging.send_each_for_multicast",
            return_value=mock_response,
        ),
    ):
        service = NotificationService(mock_db_session)
        result = await service.send_multicast(
            tokens=["token_1", "token_2"],
            title="Test chore",
            body="New chore available",
            data={"chore_id": "123"},
        )
        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failure"] == 0
        assert result["pruned"] == 0


@pytest.mark.asyncio
async def test_notification_service_prune_invalid_tokens(mock_db_session: AsyncMock):
    from firebase_admin import messaging

    mock_resp1 = MagicMock(success=True)
    mock_resp2 = MagicMock(
        success=False, exception=messaging.UnregisteredError("Token unregistered")
    )

    mock_response = MagicMock()
    mock_response.success_count = 1
    mock_response.failure_count = 1
    mock_response.responses = [mock_resp1, mock_resp2]

    with (
        patch("notifications.service.is_fcm_available", return_value=True),
        patch(
            "notifications.service.messaging.send_each_for_multicast",
            return_value=mock_response,
        ),
    ):
        service = NotificationService(mock_db_session)
        service.device_repo.delete_tokens = AsyncMock()

        result = await service.send_multicast(
            tokens=["valid_token", "invalid_token"],
            title="Test",
            body="Test message",
        )
        assert result["total"] == 2
        assert result["success"] == 1
        assert result["failure"] == 1
        assert result["pruned"] == 1
        service.device_repo.delete_tokens.assert_called_once_with(["invalid_token"])


@pytest.mark.asyncio
async def test_notification_service_notify_family_new_chore(mock_db_session: AsyncMock):
    service = NotificationService(mock_db_session)
    service.send_to_family = AsyncMock(return_value={"total": 2, "success": 2})

    family_id = uuid.uuid4()
    creator_id = uuid.uuid4()
    chore_id = uuid.uuid4()

    await service.notify_family_new_chore(
        family_id=family_id,
        creator_id=creator_id,
        creator_name="Andrey",
        chore_name="Помыть посуду",
        chore_id=chore_id,
        chore_type="planned",
    )

    assert service.send_to_family.called
    kwargs = service.send_to_family.call_args[1]
    assert kwargs["family_id"] == family_id
    assert kwargs["exclude_user_id"] == creator_id
    assert "Помыть посуду" in kwargs["title"]
    assert "Andrey" in kwargs["body"]
    assert kwargs["data"]["chore_type"] == "planned"
    assert kwargs["data"]["chore_id"] == str(chore_id)


# ==========================================
# API Endpoint Tests
# ==========================================


@pytest.mark.asyncio
async def test_api_register_device(
    async_client, mock_db_session: AsyncMock, sample_user: User
):
    now = datetime.now()
    registered_device = UserDevice(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        token="fcm_token_abcdef1234567890",
        device_type="android",
        device_name="Pixel 8",
        created_at=now,
        updated_at=now,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with patch.object(
        DeviceRepository, "register_device", AsyncMock(return_value=registered_device)
    ):
        resp = await async_client.post(
            "/api/notifications/devices",
            json={
                "token": "fcm_token_abcdef1234567890",
                "device_type": "android",
                "device_name": "Pixel 8",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["token"] == "fcm_token_abcdef1234567890"
        assert data["device_name"] == "Pixel 8"
        assert data["device_type"] == "android"


@pytest.mark.asyncio
async def test_api_list_devices(
    async_client, mock_db_session: AsyncMock, sample_user: User
):
    now = datetime.now()
    d1 = UserDevice(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        token="token_111111111111",
        device_type="android",
        device_name="Phone 1",
        created_at=now,
        updated_at=now,
    )
    d2 = UserDevice(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        token="token_222222222222",
        device_type="android",
        device_name="Phone 2",
        created_at=now,
        updated_at=now,
    )

    with patch.object(
        DeviceRepository, "get_user_devices", AsyncMock(return_value=[d1, d2])
    ):
        resp = await async_client.get("/api/notifications/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["token"] == "token_111111111111"
        assert data[1]["token"] == "token_222222222222"


@pytest.mark.asyncio
async def test_api_unregister_device(async_client, mock_db_session: AsyncMock):
    with patch.object(
        DeviceRepository, "unregister_device", AsyncMock(return_value=True)
    ):
        resp = await async_client.delete(
            "/api/notifications/devices/token_to_delete_12345"
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_api_send_test_notification(async_client, mock_db_session: AsyncMock):
    delivery_mock = {"total": 1, "success": 1, "failure": 0, "pruned": 0}
    with patch.object(
        NotificationService, "send_to_user", AsyncMock(return_value=delivery_mock)
    ):
        resp = await async_client.post(
            "/api/notifications/test",
            json={
                "title": "Ping",
                "body": "Test ping message",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "fcm_available" in data
        assert data["delivery"]["success"] == 1
