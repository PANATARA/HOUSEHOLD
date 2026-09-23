import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from core.enums import FrequencyTypeENUM
from chores.models import Chore
from users.models import User
from planned_chores.models import ChoreSchedule, PlannedChore


async def test_create_schedule_endpoint(
    async_client: AsyncClient,
    sample_chore: Chore,
    sample_user: User,
    sample_schedule: ChoreSchedule,
):
    today = datetime.date.today().isoformat()
    payload = {
        "assigned_to_id": str(sample_user.id),
        "frequency_type": "daily",
        "interval": 1,
        "starts_at": today,
    }

    with patch("chores.repository.ChoreRepository.get_by_id", new_callable=AsyncMock) as mock_chore, \
         patch("users.repository.UserRepository.get_by_id", new_callable=AsyncMock) as mock_user, \
         patch("planned_chores.services.CreateChoreSchedule.run_process", new_callable=AsyncMock) as mock_service:
        mock_chore.return_value = sample_chore
        mock_user.return_value = sample_user
        mock_service.return_value = sample_schedule

        response = await async_client.post(
            f"/api/chores/{sample_chore.id}/schedule",
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_schedule.id)
        assert data["frequency_type"] == "daily"


async def test_create_schedule_chore_not_found(
    async_client: AsyncClient,
    sample_user: User,
):
    fake_chore_id = uuid.uuid4()
    payload = {
        "assigned_to_id": str(sample_user.id),
        "frequency_type": "daily",
        "interval": 1,
        "starts_at": datetime.date.today().isoformat(),
    }

    with patch("chores.repository.ChoreRepository.get_by_id", new_callable=AsyncMock) as mock_chore:
        mock_chore.return_value = None

        response = await async_client.post(
            f"/api/chores/{fake_chore_id}/schedule",
            json=payload,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Chore not found"


async def test_get_chore_schedule_endpoint(
    async_client: AsyncClient,
    sample_chore: Chore,
    sample_schedule: ChoreSchedule,
):
    with patch("chores.repository.ChoreRepository.get_by_id", new_callable=AsyncMock) as mock_chore, \
         patch("planned_chores.repository.ChoreScheduleRepository.get_by_chore_id", new_callable=AsyncMock) as mock_sched:
        mock_chore.return_value = sample_chore
        mock_sched.return_value = sample_schedule

        response = await async_client.get(f"/api/chores/{sample_chore.id}/schedule")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_schedule.id)
        assert data["is_active"] is True


async def test_get_chore_schedule_not_found(
    async_client: AsyncClient,
    sample_chore: Chore,
):
    with patch("chores.repository.ChoreRepository.get_by_id", new_callable=AsyncMock) as mock_chore, \
         patch("planned_chores.repository.ChoreScheduleRepository.get_by_chore_id", new_callable=AsyncMock) as mock_sched:
        mock_chore.return_value = sample_chore
        mock_sched.return_value = None

        response = await async_client.get(f"/api/chores/{sample_chore.id}/schedule")
        assert response.status_code == 404


async def test_update_schedule_endpoint(
    async_client: AsyncClient,
    sample_schedule: ChoreSchedule,
):
    payload = {
        "interval": 3,
    }

    with patch("planned_chores.repository.ChoreScheduleRepository.get_by_id", new_callable=AsyncMock) as mock_get, \
         patch("planned_chores.services.UpdateChoreSchedule.run_process", new_callable=AsyncMock) as mock_service:
        mock_get.return_value = sample_schedule
        sample_schedule.interval = 3
        mock_service.return_value = sample_schedule

        response = await async_client.patch(
            f"/api/schedules/{sample_schedule.id}",
            json=payload,
        )

        assert response.status_code == 200
        assert response.json()["interval"] == 3


async def test_delete_schedule_endpoint(
    async_client: AsyncClient,
    sample_schedule: ChoreSchedule,
):
    with patch("planned_chores.repository.ChoreScheduleRepository.get_by_id", new_callable=AsyncMock) as mock_get, \
         patch("planned_chores.services.DeleteChoreSchedule.run_process", new_callable=AsyncMock) as mock_del:
        mock_get.return_value = sample_schedule
        mock_del.return_value = None

        response = await async_client.delete(f"/api/schedules/{sample_schedule.id}")
        assert response.status_code == 204


async def test_update_planned_chore_message_endpoint(
    async_client: AsyncClient,
    sample_chore: Chore,
    sample_user: User,
):
    from planned_chores.schemas import PlannedChoreResponseSchema

    planned_chore_id = uuid.uuid4()
    planned_chore = PlannedChore(
        id=planned_chore_id,
        schedule_id=None,
        chore_id=sample_chore.id,
        family_id=sample_chore.family_id,
        completed_by_id=None,
        assigned_to_id=sample_user.id,
        due_date=datetime.date.today(),
        message="Initial message",
        is_active=True,
    )
    full_response_data = {
        "id": planned_chore_id,
        "schedule_id": None,
        "chore": {
            "id": sample_chore.id,
            "name": sample_chore.name,
            "description": sample_chore.description,
            "icon": sample_chore.icon,
            "icon_color": sample_chore.icon_color,
            "icon_bg": sample_chore.icon_bg,
            "valuation": sample_chore.valuation,
            "default_chore_id": None,
        },
        "completed_by": None,
        "assigned_to": {
            "id": sample_user.id,
            "username": sample_user.username,
            "name": sample_user.name,
            "icon": "icon",
            "icon_color": "#fff",
            "icon_bg": "#000",
            "experience": 0,
        },
        "due_date": datetime.date.today(),
        "message": "Updated message text",
    }
    mock_resp_schema = PlannedChoreResponseSchema.model_validate(full_response_data)

    payload = {"message": "Updated message text"}

    with patch("planned_chores.repository.PlannedChoreRepository.get_by_id", new_callable=AsyncMock) as mock_get, \
         patch("planned_chores.services.UpdatePlannedChoreMessage.run_process", new_callable=AsyncMock) as mock_service, \
         patch("planned_chores.repository.PlannedChoreRepository.get_planned_chore_by_id", new_callable=AsyncMock) as mock_full:
        mock_get.return_value = planned_chore
        mock_service.return_value = planned_chore
        mock_full.return_value = mock_resp_schema

        response = await async_client.patch(
            f"/api/chores/planned/{planned_chore_id}/message",
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(planned_chore_id)
        assert data["message"] == "Updated message text"


async def test_update_planned_chore_message_endpoint_alias(
    async_client: AsyncClient,
    sample_chore: Chore,
    sample_user: User,
):
    from planned_chores.schemas import PlannedChoreResponseSchema

    planned_chore_id = uuid.uuid4()
    planned_chore = PlannedChore(
        id=planned_chore_id,
        schedule_id=None,
        chore_id=sample_chore.id,
        family_id=sample_chore.family_id,
        completed_by_id=None,
        assigned_to_id=sample_user.id,
        due_date=datetime.date.today(),
        message="Initial message",
        is_active=True,
    )
    full_response_data = {
        "id": planned_chore_id,
        "schedule_id": None,
        "chore": {
            "id": sample_chore.id,
            "name": sample_chore.name,
            "description": sample_chore.description,
            "icon": sample_chore.icon,
            "icon_color": sample_chore.icon_color,
            "icon_bg": sample_chore.icon_bg,
            "valuation": sample_chore.valuation,
            "default_chore_id": None,
        },
        "completed_by": None,
        "assigned_to": {
            "id": sample_user.id,
            "username": sample_user.username,
            "name": sample_user.name,
            "icon": "icon",
            "icon_color": "#fff",
            "icon_bg": "#000",
            "experience": 0,
        },
        "due_date": datetime.date.today(),
        "message": "Updated via alias",
    }
    mock_resp_schema = PlannedChoreResponseSchema.model_validate(full_response_data)

    payload = {"message": "Updated via alias"}

    with patch("planned_chores.repository.PlannedChoreRepository.get_by_id", new_callable=AsyncMock) as mock_get, \
         patch("planned_chores.services.UpdatePlannedChoreMessage.run_process", new_callable=AsyncMock) as mock_service, \
         patch("planned_chores.repository.PlannedChoreRepository.get_planned_chore_by_id", new_callable=AsyncMock) as mock_full:
        mock_get.return_value = planned_chore
        mock_service.return_value = planned_chore
        mock_full.return_value = mock_resp_schema

        response = await async_client.patch(
            f"/api/chores/planned/{planned_chore_id}",
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(planned_chore_id)
        assert data["message"] == "Updated via alias"


async def test_update_planned_chore_message_validation_error(
    async_client: AsyncClient,
):
    planned_chore_id = uuid.uuid4()
    # Message too long (> 2000 chars)
    response = await async_client.patch(
        f"/api/chores/planned/{planned_chore_id}/message",
        json={"message": "a" * 2001},
    )
    assert response.status_code == 422

