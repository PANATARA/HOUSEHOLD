import datetime
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from core.enums import FrequencyTypeENUM
from chores.models import Chore
from users.models import User
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.schemas import ChoreScheduleUpdateSchema
from planned_chores.services import (
    CreateChoreSchedule,
    UpdateChoreSchedule,
    DeleteChoreSchedule,
    GeneratePlannedChores,
)


def test_matches_daily(mock_db_session: AsyncMock, sample_schedule: ChoreSchedule):
    generator = GeneratePlannedChores(db_session=mock_db_session)
    sample_schedule.frequency_type = FrequencyTypeENUM.daily
    sample_schedule.starts_at = datetime.date(2026, 9, 1)
    sample_schedule.interval = 3

    # Day 0 (Sep 1): delta 0 % 3 == 0 -> True
    assert generator._matches_daily(sample_schedule, datetime.date(2026, 9, 1)) is True
    # Day 1 (Sep 2): delta 1 % 3 != 0 -> False
    assert generator._matches_daily(sample_schedule, datetime.date(2026, 9, 2)) is False
    # Day 2 (Sep 3): delta 2 % 3 != 0 -> False
    assert generator._matches_daily(sample_schedule, datetime.date(2026, 9, 3)) is False
    # Day 3 (Sep 4): delta 3 % 3 == 0 -> True
    assert generator._matches_daily(sample_schedule, datetime.date(2026, 9, 4)) is True


def test_matches_weekly_bitmask(mock_db_session: AsyncMock, sample_schedule: ChoreSchedule):
    generator = GeneratePlannedChores(db_session=mock_db_session)
    sample_schedule.frequency_type = FrequencyTypeENUM.weekly
    # Monday 2026-09-07
    sample_schedule.starts_at = datetime.date(2026, 9, 7)
    sample_schedule.interval = 1
    # 1 (Mon) | 4 (Wed) | 16 (Fri) = 21
    sample_schedule.days_of_week = 21

    # Mon Sep 7 -> True
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 7)) is True
    # Tue Sep 8 -> False
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 8)) is False
    # Wed Sep 9 -> True
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 9)) is True
    # Thu Sep 10 -> False
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 10)) is False
    # Fri Sep 11 -> True
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 11)) is True
    # Sat Sep 12 -> False
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 12)) is False
    # Sun Sep 13 -> False
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 13)) is False


def test_matches_weekly_biweekly(mock_db_session: AsyncMock, sample_schedule: ChoreSchedule):
    generator = GeneratePlannedChores(db_session=mock_db_session)
    sample_schedule.frequency_type = FrequencyTypeENUM.weekly
    # Monday 2026-09-07, interval = 2 weeks
    sample_schedule.starts_at = datetime.date(2026, 9, 7)
    sample_schedule.interval = 2
    sample_schedule.days_of_week = 1  # Monday only

    # Week 0 (Sep 7): True
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 7)) is True
    # Week 1 (Sep 14): False
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 14)) is False
    # Week 2 (Sep 21): True
    assert generator._matches_weekly(sample_schedule, datetime.date(2026, 9, 21)) is True


def test_matches_monthly_clamp(mock_db_session: AsyncMock, sample_schedule: ChoreSchedule):
    generator = GeneratePlannedChores(db_session=mock_db_session)
    sample_schedule.frequency_type = FrequencyTypeENUM.monthly
    sample_schedule.starts_at = datetime.date(2026, 1, 31)
    sample_schedule.interval = 1
    sample_schedule.day_of_month = 31

    # Jan 31 -> True
    assert generator._matches_monthly(sample_schedule, datetime.date(2026, 1, 31)) is True
    # Feb 28 in 2026 (non-leap year, last day of Feb) -> True (clamped)
    assert generator._matches_monthly(sample_schedule, datetime.date(2026, 2, 28)) is True
    # Mar 31 -> True
    assert generator._matches_monthly(sample_schedule, datetime.date(2026, 3, 31)) is True
    # Mar 30 -> False
    assert generator._matches_monthly(sample_schedule, datetime.date(2026, 3, 30)) is False


async def test_create_chore_schedule_service(
    mock_db_session: AsyncMock,
    sample_chore: Chore,
    sample_user: User,
):
    today = datetime.date.today()
    service = CreateChoreSchedule(
        chore=sample_chore,
        assigned_to=sample_user,
        created_by=sample_user,
        frequency_type=FrequencyTypeENUM.daily,
        interval=1,
        days_of_week=None,
        day_of_month=None,
        starts_at=today,
        ends_at=None,
        db_session=mock_db_session,
    )

    with patch("planned_chores.services.ChoreScheduleRepository.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = ChoreSchedule(
            id=uuid.uuid4(),
            chore_id=sample_chore.id,
            family_id=sample_chore.family_id,
            assigned_to_id=sample_user.id,
            created_by=sample_user.id,
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            days_of_week=None,
            day_of_month=None,
            starts_at=today,
            ends_at=None,
            is_active=True,
        )
        created = await service.run_process()
        assert created.frequency_type == FrequencyTypeENUM.daily
        assert created.interval == 1
        mock_create.assert_called_once()


async def test_create_chore_schedule_different_family_fails(
    mock_db_session: AsyncMock,
    sample_chore: Chore,
    sample_user: User,
):
    # Set user to different family
    sample_user.family_id = uuid.uuid4()
    service = CreateChoreSchedule(
        chore=sample_chore,
        assigned_to=sample_user,
        created_by=sample_user,
        frequency_type=FrequencyTypeENUM.daily,
        interval=1,
        days_of_week=None,
        day_of_month=None,
        starts_at=datetime.date.today(),
        ends_at=None,
        db_session=mock_db_session,
    )
    with pytest.raises(ValueError) as exc_info:
        await service.run_process()
    assert "does not belong to the chore's family" in str(exc_info.value)


async def test_update_chore_schedule_service(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    body = ChoreScheduleUpdateSchema(interval=3)
    service = UpdateChoreSchedule(
        schedule=sample_schedule,
        body=body,
        db_session=mock_db_session,
    )

    with patch("planned_chores.services.ChoreScheduleRepository.update", new_callable=AsyncMock) as mock_update, \
         patch("planned_chores.services.GeneratePlannedChores.reconcile_for_schedule", new_callable=AsyncMock) as mock_reconcile:
        mock_update.return_value = sample_schedule
        updated = await service.run_process()
        assert updated.interval == 3
        mock_update.assert_called_once()
        mock_reconcile.assert_called_once()


async def test_delete_chore_schedule_service(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    uncompleted_chore = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=datetime.date.today(),
        message="",
        is_active=True,
    )

    # Mock DB query returning the uncompleted chore
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [uncompleted_chore]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    service = DeleteChoreSchedule(
        schedule=sample_schedule,
        db_session=mock_db_session,
        revoke_completed_awards=False,
    )

    with patch("planned_chores.services.ChoreScheduleRepository.soft_delete", new_callable=AsyncMock) as mock_soft_del, \
         patch("planned_chores.services.PlannedChoreRepository.hard_delete", new_callable=AsyncMock) as mock_hard_del:
        await service.run_process()
        mock_soft_del.assert_called_once_with(sample_schedule.id)
        mock_hard_del.assert_called_once_with(uncompleted_chore.id)
        assert sample_schedule.is_active is False


async def test_update_planned_chore_message_service(
    mock_db_session: AsyncMock,
    sample_chore: Chore,
    sample_user: User,
):
    from planned_chores.services import UpdatePlannedChoreMessage

    planned_chore = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=None,
        chore_id=sample_chore.id,
        family_id=sample_chore.family_id,
        completed_by_id=None,
        assigned_to_id=sample_user.id,
        due_date=datetime.date.today(),
        message="Initial message",
        is_active=True,
    )

    with patch("planned_chores.services.PlannedChoreRepository.update", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = planned_chore
        service = UpdatePlannedChoreMessage(
            planned_chore=planned_chore,
            message="Updated message text",
            db_session=mock_db_session,
        )
        result = await service.run_process()

        assert result.message == "Updated message text"
        mock_update.assert_called_once_with(planned_chore)

