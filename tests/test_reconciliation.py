import datetime
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from core.enums import FrequencyTypeENUM
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.services import GeneratePlannedChores


async def test_reconciliation_deletes_unmatched_uncompleted_chores(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    """
    When schedule is changed from interval=1 to interval=3:
    - Day 0 (today): delta 0 -> matches -> kept
    - Day 1 (tomorrow): delta 1 -> unmatched -> deleted
    - Day 2 (in 2 days): delta 2 -> unmatched -> deleted
    - Day 3 (in 3 days): delta 3 -> matches -> kept
    """
    today = datetime.date.today()
    sample_schedule.frequency_type = FrequencyTypeENUM.daily
    sample_schedule.starts_at = today
    sample_schedule.interval = 3
    sample_schedule.is_active = True

    chore_today = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=today,
        message="",
        is_active=True,
    )
    chore_day1 = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=today + datetime.timedelta(days=1),
        message="",
        is_active=True,
    )
    chore_day2 = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=today + datetime.timedelta(days=2),
        message="",
        is_active=True,
    )
    chore_day3 = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=today + datetime.timedelta(days=3),
        message="",
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [chore_today, chore_day1, chore_day2, chore_day3]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    generator = GeneratePlannedChores(db_session=mock_db_session)

    with patch("planned_chores.services.PlannedChoreRepository.hard_delete", new_callable=AsyncMock) as mock_delete, \
         patch("planned_chores.services.ChoreScheduleRepository.update", new_callable=AsyncMock):
        await generator.reconcile_for_schedule(sample_schedule, from_date=today)

        # Day 1 and Day 2 should be deleted
        assert mock_delete.call_count == 2
        deleted_ids = [call.args[0] for call in mock_delete.call_args_list]
        assert chore_day1.id in deleted_ids
        assert chore_day2.id in deleted_ids
        assert chore_today.id not in deleted_ids
        assert chore_day3.id not in deleted_ids


async def test_reconciliation_preserves_completed_chores(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    """
    A completed chore (completed_by_id is not None) must NEVER be deleted,
    even if its date does not match the new recurrence interval.
    """
    today = datetime.date.today()
    sample_schedule.frequency_type = FrequencyTypeENUM.daily
    sample_schedule.starts_at = today
    sample_schedule.interval = 3
    sample_schedule.is_active = True

    # Day 1 does not match interval 3, but is already COMPLETED
    completed_chore_day1 = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=uuid.uuid4(),
        due_date=today + datetime.timedelta(days=1),
        message="",
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [completed_chore_day1]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    generator = GeneratePlannedChores(db_session=mock_db_session)

    with patch("planned_chores.services.PlannedChoreRepository.hard_delete", new_callable=AsyncMock) as mock_delete, \
         patch("planned_chores.services.ChoreScheduleRepository.update", new_callable=AsyncMock):
        await generator.reconcile_for_schedule(sample_schedule, from_date=today)
        mock_delete.assert_not_called()


async def test_reconciliation_updates_assigned_user(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    """
    When schedule assigned_to_id changes, remaining matching uncompleted chores
    must have their assigned_to_id updated.
    """
    today = datetime.date.today()
    new_user_id = uuid.uuid4()
    sample_schedule.assigned_to_id = new_user_id
    sample_schedule.frequency_type = FrequencyTypeENUM.daily
    sample_schedule.starts_at = today
    sample_schedule.interval = 1
    sample_schedule.is_active = True

    chore = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        assigned_to_id=uuid.uuid4(),  # old user
        due_date=today,
        message="",
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [chore]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    generator = GeneratePlannedChores(db_session=mock_db_session)

    with patch("planned_chores.services.ChoreScheduleRepository.update", new_callable=AsyncMock):
        await generator.reconcile_for_schedule(sample_schedule, from_date=today)
        assert chore.assigned_to_id == new_user_id


async def test_reconciliation_deactivates_schedule_cleans_up(
    mock_db_session: AsyncMock,
    sample_schedule: ChoreSchedule,
):
    """
    When schedule is deactivated (is_active=False), all future uncompleted chores
    must be deleted.
    """
    today = datetime.date.today()
    sample_schedule.is_active = False

    chore1 = PlannedChore(
        id=uuid.uuid4(),
        schedule_id=sample_schedule.id,
        chore_id=sample_schedule.chore_id,
        family_id=sample_schedule.family_id,
        completed_by_id=None,
        due_date=today + datetime.timedelta(days=1),
        message="",
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [chore1]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute.return_value = mock_result

    generator = GeneratePlannedChores(db_session=mock_db_session)

    with patch("planned_chores.services.PlannedChoreRepository.hard_delete", new_callable=AsyncMock) as mock_delete:
        await generator.reconcile_for_schedule(sample_schedule, from_date=today)
        mock_delete.assert_called_once_with(chore1.id)
