import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from statistics.repository import StatsPostgresRepository
from statistics.schemas import DateRangeSchema


@pytest.mark.asyncio
async def test_stats_repo_family_members_includes_quick_planned_chore(
    mock_db_session: AsyncMock,
):
    family_id = uuid.uuid4()
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.all.return_value = [(user1_id, 5), (user2_id, 3)]
    mock_db_session.execute.return_value = mock_result

    repo = StatsPostgresRepository(db_session=mock_db_session)
    interval = DateRangeSchema(
        start=datetime.datetime(2026, 9, 1),
        end=datetime.datetime(2026, 9, 30),
    )
    result = await repo.get_family_members_by_chores_completions(family_id, interval)

    assert len(result) == 2
    assert result[0].user_id == user1_id
    assert result[0].chores_completions_counts == 5

    # Verify SQL query checks both planned_chore and quick_planned_chore
    call_args = mock_db_session.execute.call_args
    sql_text = str(call_args[0][0])
    assert "planned_chore" in sql_text
    assert "quick_planned_chore" in sql_text


@pytest.mark.asyncio
async def test_stats_repo_family_chore_completion_count_includes_quick_planned_chore(
    mock_db_session: AsyncMock,
):
    family_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.all.return_value = [(12,)]
    mock_db_session.execute.return_value = mock_result

    repo = StatsPostgresRepository(db_session=mock_db_session)
    count = await repo.get_family_chore_completion_count(family_id)

    assert count == 12

    call_args = mock_db_session.execute.call_args
    sql_text = str(call_args[0][0])
    assert "planned_chore" in sql_text
    assert "quick_planned_chore" in sql_text


@pytest.mark.asyncio
async def test_stats_repo_heatmaps_and_streaks_include_quick_planned_chore(
    mock_db_session: AsyncMock,
):
    family_id = uuid.uuid4()
    user_id = uuid.uuid4()
    d = datetime.date(2026, 9, 18)

    mock_result = MagicMock()
    mock_result.all.return_value = [(d, 4)]
    mock_result.scalar_one.return_value = 7
    mock_db_session.execute.return_value = mock_result

    repo = StatsPostgresRepository(db_session=mock_db_session)

    # Heatmap
    heatmap = await repo.get_family_heatmap(family_id)
    assert heatmap[d] == 4
    sql_text = str(mock_db_session.execute.call_args[0][0])
    assert "quick_planned_chore" in sql_text

    # User streak
    streak = await repo.get_user_current_streak(user_id)
    assert streak == 7
    sql_text = str(mock_db_session.execute.call_args[0][0])
    assert "quick_planned_chore" in sql_text
