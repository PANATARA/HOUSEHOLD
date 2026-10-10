"""
Integration tests for the Statistics module.

Tests verify:
- Real SQL queries for chore counts, streaks, experience
- Raw SQL queries in StatsPostgresRepository return correct values
  against known data inserted via IntegrationFactory
"""

import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import FrequencyTypeENUM
from planned_chores.models import PlannedChore, QuickPlannedChore


class TestStatisticsRepository:
    """Tests for StatsPostgresRepository running raw SQL on real PostgreSQL."""

    async def _get_repo(self, db_session: AsyncSession):
        from statistics.repository import StatsPostgresRepository
        return StatsPostgresRepository(db_session)

    # ── Chore Completion Count ────────────────────────────────────────────────

    async def test_family_completion_count_zero_when_no_completions(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = await self._get_repo(db_session)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id
        )
        assert count == 0

    async def test_family_completion_count_counts_completed_planned_chores(
        self, db_session: AsyncSession, integration_factory
    ):
        # Create 3 completed planned chores
        for _ in range(3):
            await integration_factory.create_planned_chore(
                due_date=datetime.date.today(),
                completed_by=integration_factory.user,
            )
        repo = await self._get_repo(db_session)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id
        )
        assert count >= 3

    async def test_family_completion_count_includes_quick_chores(
        self, db_session: AsyncSession, integration_factory
    ):
        await integration_factory.create_quick_chore(
            due_date=datetime.date.today(),
            completed_by=integration_factory.user,
        )
        repo = await self._get_repo(db_session)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id
        )
        assert count >= 1

    async def test_family_completion_count_excludes_uncompleted(
        self, db_session: AsyncSession, integration_factory
    ):
        # Uncompleted chore
        await integration_factory.create_planned_chore(due_date=datetime.date.today())
        repo = await self._get_repo(db_session)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id
        )
        assert count == 0

    async def test_family_completion_count_excludes_inactive(
        self, db_session: AsyncSession, integration_factory
    ):
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=integration_factory.user,
        )
        pc.is_active = False
        db_session.add(pc)
        await db_session.flush()

        repo = await self._get_repo(db_session)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id
        )
        assert count == 0

    async def test_completion_count_with_date_interval_filter(
        self, db_session: AsyncSession, integration_factory
    ):
        from statistics.schemas import DateRangeSchema
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        # Completed today
        await integration_factory.create_planned_chore(
            due_date=today, completed_by=integration_factory.user
        )
        # Completed yesterday (outside range)
        await integration_factory.create_planned_chore(
            due_date=yesterday, completed_by=integration_factory.user
        )

        repo = await self._get_repo(db_session)
        interval = DateRangeSchema(start=today, end=today)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id,
            interval=interval,
        )
        assert count == 1

    # ── User Completion Count ─────────────────────────────────────────────────

    async def test_user_chore_count_for_multiple_users(
        self, db_session: AsyncSession, integration_factory
    ):
        user1 = integration_factory.user
        user2 = integration_factory.user2

        # user1 completes 2, user2 completes 1
        for _ in range(2):
            await integration_factory.create_planned_chore(
                due_date=datetime.date.today(),
                completed_by=user1,
            )
        await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user2,
        )

        repo = await self._get_repo(db_session)
        results = await repo.get_users_chore_completion_count(
            users_ids=[user1.id, user2.id]
        )

        counts = {r.user_id: r.chores_completions_counts for r in results}
        assert counts[user1.id] >= 2
        assert counts[user2.id] >= 1

    async def test_user_chore_count_returns_zero_for_no_completions(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = await self._get_repo(db_session)
        new_id = uuid.uuid4()
        results = await repo.get_users_chore_completion_count(users_ids=[new_id])
        assert results[0].chores_completions_counts == 0

    # ── Streak Tests ──────────────────────────────────────────────────────────

    async def test_family_streak_zero_with_no_completions(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = await self._get_repo(db_session)
        streak = await repo.get_family_current_streak(
            family_id=integration_factory.family.id
        )
        assert streak == 0

    async def test_family_streak_one_for_single_completion_today(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

        await integration_factory.create_planned_chore(
            due_date=db_today,
            completed_by=integration_factory.user,
        )
        repo = await self._get_repo(db_session)
        streak = await repo.get_family_current_streak(
            family_id=integration_factory.family.id
        )
        assert streak >= 1

    async def test_family_streak_consecutive_days(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

        for i in range(3):
            day = db_today - datetime.timedelta(days=i)
            await integration_factory.create_planned_chore(
                due_date=day,
                completed_by=integration_factory.user,
            )
        repo = await self._get_repo(db_session)
        streak = await repo.get_family_current_streak(
            family_id=integration_factory.family.id
        )
        assert streak >= 3

    async def test_streak_breaks_on_missed_day(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

        # Complete today and 3 days ago (gap of 2 days)
        await integration_factory.create_planned_chore(
            due_date=db_today,
            completed_by=integration_factory.user,
        )
        await integration_factory.create_planned_chore(
            due_date=db_today - datetime.timedelta(days=3),
            completed_by=integration_factory.user,
        )
        repo = await self._get_repo(db_session)
        streak = await repo.get_family_current_streak(
            family_id=integration_factory.family.id
        )
        # Streak should be 1 (only today counts because day -3 is not consecutive)
        assert streak == 1

    async def test_user_streak_zero_with_no_completions(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = await self._get_repo(db_session)
        streak = await repo.get_user_current_streak(
            user_id=integration_factory.user.id
        )
        assert streak == 0

    async def test_user_streak_counts_only_own_completions(
        self, db_session: AsyncSession, integration_factory
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

        # user2 completes, not user1
        await integration_factory.create_planned_chore(
            due_date=db_today,
            completed_by=integration_factory.user2,
        )
        repo = await self._get_repo(db_session)
        streak = await repo.get_user_current_streak(
            user_id=integration_factory.user.id  # user1 streak
        )
        assert streak == 0

        streak2 = await repo.get_user_current_streak(
            user_id=integration_factory.user2.id
        )
        assert streak2 >= 1


# ── Statistics Counting Helper Tests ─────────────────────────────────────────

class TestStatisticsCountHelpers:
    """Test the _add_date_interval helper logic indirectly."""

    async def test_count_with_only_start_date(
        self, db_session: AsyncSession, integration_factory
    ):
        from statistics.repository import StatsPostgresRepository
        from statistics.schemas import DateRangeSchema

        today = datetime.date.today()
        await integration_factory.create_planned_chore(
            due_date=today, completed_by=integration_factory.user
        )

        repo = StatsPostgresRepository(db_session)
        interval = DateRangeSchema(start=today, end=None)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id, interval=interval
        )
        assert count >= 1

    async def test_count_with_only_end_date(
        self, db_session: AsyncSession, integration_factory
    ):
        from statistics.repository import StatsPostgresRepository
        from statistics.schemas import DateRangeSchema

        today = datetime.date.today()
        await integration_factory.create_planned_chore(
            due_date=today, completed_by=integration_factory.user
        )

        repo = StatsPostgresRepository(db_session)
        interval = DateRangeSchema(start=None, end=today)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id, interval=interval
        )
        assert count >= 1

    async def test_count_with_future_start_date_returns_zero(
        self, db_session: AsyncSession, integration_factory
    ):
        from statistics.repository import StatsPostgresRepository
        from statistics.schemas import DateRangeSchema

        today = datetime.date.today()
        await integration_factory.create_planned_chore(
            due_date=today, completed_by=integration_factory.user
        )

        future = today + datetime.timedelta(days=30)
        repo = StatsPostgresRepository(db_session)
        interval = DateRangeSchema(start=future, end=None)
        count = await repo.get_family_chore_completion_count(
            family_id=integration_factory.family.id, interval=interval
        )
        assert count == 0
