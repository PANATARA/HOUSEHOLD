"""
Integration tests for chore schedule generation, reconciliation, and worker tasks:
- GeneratePlannedChores (daily, weekly bitmask, monthly, idempotency, horizon)
- UpdateChoreSchedule (reconciliation with uncompleted chores)
- DeleteChoreSchedule (cascade soft/hard deletion, award revocation)
- worker.generate_planned_chores_task (ARQ worker cron execution)
"""

import datetime
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import FrequencyTypeENUM
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.repository import ChoreScheduleRepository, PlannedChoreRepository
from planned_chores.schemas import ChoreScheduleUpdateSchema
from planned_chores.services import (
    CompletePlannedChore,
    DeleteChoreSchedule,
    GeneratePlannedChores,
    UpdateChoreSchedule,
)
from worker import generate_planned_chores_task


class TestGeneratePlannedChores:
    """Integration tests for the recurring chore generation engine against real PostgreSQL."""

    async def test_generate_daily_schedule_creates_chores(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        # Create a daily schedule every 2 days for 10 days
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=2,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=10),
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=2)
        generated = await generator.generate_for_schedule(schedule)

        # Dates: today, today+2, today+4, today+6, today+8, today+10 -> 6 chores
        assert len(generated) == 6
        due_dates = [c.due_date for c in generated]
        assert today in due_dates
        assert today + datetime.timedelta(days=2) in due_dates
        assert today + datetime.timedelta(days=10) in due_dates

        # Re-query DB to verify persistence
        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.schedule_id == schedule.id)
        )
        db_chores = list(result.scalars().all())
        assert len(db_chores) == 6

    async def test_generate_weekly_schedule_matches_days_of_week(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        # Find next Monday (weekday == 0)
        days_ahead = (0 - today.weekday()) % 7
        next_monday = today + datetime.timedelta(days=days_ahead)

        # Mon (1) and Wed (4) -> bitmask = (1 << 0) | (1 << 2) = 1 | 4 = 5
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.weekly,
            interval=1,
            days_of_week=5,
            starts_at=next_monday,
            ends_at=next_monday + datetime.timedelta(days=13),  # 2 full weeks
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=3)
        generated = await generator.generate_for_schedule(
            schedule=schedule,
            generate_until=next_monday + datetime.timedelta(days=13),
        )

        # 2 weeks * 2 days/week (Mon, Wed) = 4 chores
        assert len(generated) == 4
        for chore in generated:
            assert chore.due_date.weekday() in (0, 2)  # Monday or Wednesday

    async def test_generate_monthly_schedule(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        # Schedule on the 15th of every month
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.monthly,
            interval=1,
            day_of_month=15,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=60),
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=8)
        generated = await generator.generate_for_schedule(
            schedule=schedule,
            generate_until=today + datetime.timedelta(days=60),
        )

        for chore in generated:
            assert chore.due_date.day == 15

    async def test_strict_idempotency_does_not_duplicate_chores(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=5),
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)

        # First run generates 6 chores (days 0..5)
        first_run = await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=5)
        )
        assert len(first_run) == 6

        # Second run with same horizon generates 0 new chores
        second_run = await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=5)
        )
        assert len(second_run) == 0

        # Total in DB is still 6
        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.schedule_id == schedule.id)
        )
        assert len(result.scalars().all()) == 6

    async def test_inactive_schedule_generates_nothing(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
        )
        schedule.is_active = False
        db_session.add(schedule)
        await db_session.flush()

        generator = GeneratePlannedChores(db_session=db_session)
        generated = await generator.generate_for_schedule(schedule)
        assert generated == []

    async def test_generate_for_family_processes_all_active_family_schedules(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        # Create 2 schedules for family
        s1 = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=2,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=4),
        )
        chore2 = await integration_factory.create_chore("Mop Floors")
        s2 = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=3,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=4),
            chore=chore2,
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        count = await generator.generate_for_family(integration_factory.family.id)

        # s1: 0, 2, 4 -> 3
        # s2: 0, 3 -> 2
        # Total = 5
        assert count == 5

    async def test_process_runs_across_all_active_schedules(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=2),
        )

        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        count = await generator.process()
        assert count >= 3


# ─── Schedule Reconciliation Tests ─────────────────────────────────────────────


class TestScheduleReconciliation:
    """Tests for reconcile_for_schedule when schedule changes."""

    async def test_reconcile_removes_uncompleted_chores_that_no_longer_match(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        # Schedule was daily (interval=1)
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=4),
        )
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=4)
        )

        # Now update schedule to interval=2 (every 2 days)
        schedule.interval = 2
        db_session.add(schedule)
        await db_session.flush()

        await generator.reconcile_for_schedule(
            schedule,
            from_date=today,
            generate_until=today + datetime.timedelta(days=4),
        )

        result = await db_session.execute(
            select(PlannedChore)
            .where(PlannedChore.schedule_id == schedule.id)
            .order_by(PlannedChore.due_date.asc())
        )
        remaining = list(result.scalars().all())
        # Should now only have today, today+2, today+4 (3 chores)
        assert len(remaining) == 3
        dates = [c.due_date for c in remaining]
        assert dates == [today, today + datetime.timedelta(days=2), today + datetime.timedelta(days=4)]

    async def test_reconcile_never_deletes_completed_chores(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=4),
        )
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=4)
        )

        # Mark chore on today+1 as completed
        query = select(PlannedChore).where(
            PlannedChore.schedule_id == schedule.id,
            PlannedChore.due_date == today + datetime.timedelta(days=1),
        )
        chore_day1 = (await db_session.execute(query)).scalar_one()
        await CompletePlannedChore(
            planned_chore=chore_day1,
            completed_by=integration_factory.user,
            db_session=db_session,
        ).run_process()

        # Update schedule to interval=2 (which ordinarily would prune day 1)
        schedule.interval = 2
        db_session.add(schedule)
        await db_session.flush()

        await generator.reconcile_for_schedule(
            schedule,
            from_date=today,
            generate_until=today + datetime.timedelta(days=4),
        )

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.schedule_id == schedule.id)
        )
        chores = list(result.scalars().all())
        due_dates = [c.due_date for c in chores]

        # Day 1 must still exist because it was completed!
        assert today + datetime.timedelta(days=1) in due_dates

    async def test_reconcile_synchronizes_assigned_user_id(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=2),
            assigned_to=integration_factory.user,
        )
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=2)
        )

        # Reassign schedule to user2
        schedule.assigned_to_id = integration_factory.user2.id
        db_session.add(schedule)
        await db_session.flush()

        await generator.reconcile_for_schedule(
            schedule,
            from_date=today,
            generate_until=today + datetime.timedelta(days=2),
        )

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.schedule_id == schedule.id)
        )
        for chore in result.scalars().all():
            assert chore.assigned_to_id == integration_factory.user2.id


# ─── Schedule Lifecycle Services ──────────────────────────────────────────────


class TestScheduleLifecycleServices:
    """Tests for UpdateChoreSchedule and DeleteChoreSchedule."""

    async def test_update_chore_schedule_service_updates_and_reconciles(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=5),
        )
        # Generate chores initially
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=5)
        )

        # Update via service to interval=3
        body = ChoreScheduleUpdateSchema(interval=3)
        svc = UpdateChoreSchedule(
            schedule=schedule,
            body=body,
            db_session=db_session,
        )
        updated = await svc.run_process()
        assert updated.interval == 3

        # Confirm DB shows updated chores (only today, today+3)
        result = await db_session.execute(
            select(PlannedChore)
            .where(PlannedChore.schedule_id == schedule.id)
            .order_by(PlannedChore.due_date.asc())
        )
        chores = list(result.scalars().all())
        assert len(chores) == 2
        assert chores[0].due_date == today
        assert chores[1].due_date == today + datetime.timedelta(days=3)

    async def test_delete_chore_schedule_soft_deletes_and_cleans_uncompleted(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=3),
        )
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=3)
        )

        svc = DeleteChoreSchedule(
            schedule=schedule,
            db_session=db_session,
            revoke_completed_awards=False,
        )
        await svc.run_process()

        # Schedule is soft deleted
        assert schedule.is_active is False

        # Uncompleted chores are hard deleted
        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.schedule_id == schedule.id)
        )
        assert len(result.scalars().all()) == 0

    async def test_delete_chore_schedule_revokes_completed_awards(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        schedule = await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=2),
        )
        generator = GeneratePlannedChores(db_session=db_session, horizon_weeks=1)
        await generator.generate_for_schedule(
            schedule, generate_until=today + datetime.timedelta(days=2)
        )

        # Complete the first chore
        query = select(PlannedChore).where(
            PlannedChore.schedule_id == schedule.id,
            PlannedChore.due_date == today,
        )
        c0 = (await db_session.execute(query)).scalar_one()
        await CompletePlannedChore(
            planned_chore=c0,
            completed_by=integration_factory.user,
            db_session=db_session,
        ).run_process()

        # User gained experience
        user = integration_factory.user
        await db_session.refresh(user)
        initial_xp = user.experience
        assert initial_xp >= integration_factory.chore.valuation

        # Delete with revoke_completed_awards=True
        svc = DeleteChoreSchedule(
            schedule=schedule,
            db_session=db_session,
            revoke_completed_awards=True,
        )
        await svc.run_process()

        # User experience was decremented
        await db_session.refresh(user)
        assert user.experience == initial_xp - integration_factory.chore.valuation


# ─── Worker Task Integration ───────────────────────────────────────────────────


class TestWorkerCronTask:
    """Tests the background ARQ worker cron function against real DB."""

    async def test_generate_planned_chores_task_runs_successfully(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        await integration_factory.create_schedule(
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=today + datetime.timedelta(days=3),
        )

        from sqlalchemy.orm import sessionmaker

        worker_sessionmaker = sessionmaker(
            db_session.bind,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        with patch("worker.async_session_maker", worker_sessionmaker):
            count = await generate_planned_chores_task(ctx={})
            assert count >= 4
