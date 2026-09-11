import calendar
import datetime
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from config import ENABLE_CLICKHOUSE
from core.enums import FrequencyTypeENUM
from core.exceptions.chores_completion import ChoreCompletionCanNotBeChanged
from core.services import BaseService
from core.validators import (
    validate_date_is_not_in_past,
    validate_planned_chore_is_completed,
    validate_planned_chore_is_not_completed,
    validate_quick_planned_chore_is_completed,
    validate_quick_planned_chore_is_not_completed,
)
from database_connection import rabbit_client
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from planned_chores.repository import (
    ChoreScheduleRepository,
    PlannedChoreRepository,
    QuickPlannedChoreRepository,
)
from planned_chores.schemas import (
    ChoreScheduleCreateSchema,
    ChoreScheduleUpdateSchema,
    QuickPlannedChoreCreateSchema,
    QuickPlannedChoreUpdateSchema,
)
from families.repository import FamilyRepository
from users.repository import UserRepository
from users.models import User
from wallets.models import RewardTransaction
from wallets.services import AwardService, QuickAwardService


async def publish_chore_completion_event(
    planned_chore: PlannedChore, sign: int
) -> None:
    """
    sign=1  — the PlannedChore is calculated in statistics (completed)
    sign=-1 — the PlannedChore has been removed from statistics (execution canceled or the completed task has been deleted)
    """
    message = {
        "id": str(planned_chore.id),
        "chore_id": str(planned_chore.chore_id),
        "family_id": str(planned_chore.family_id),
        "completed_by_id": str(planned_chore.completed_by_id),
        "assigned_to_id": str(planned_chore.assigned_to_id),
        "due_date": planned_chore.due_date.isoformat(),
        "sign": sign,
    }
    await rabbit_client.publish(message=message)


async def publish_quick_chore_completion_event(
    quick_chore: QuickPlannedChore, sign: int
) -> None:
    message = {
        "id": str(quick_chore.id),
        "chore_id": None,
        "family_id": str(quick_chore.family_id),
        "completed_by_id": str(quick_chore.completed_by_id),
        "assigned_to_id": str(quick_chore.assigned_to_id)
        if quick_chore.assigned_to_id
        else None,
        "due_date": quick_chore.due_date.isoformat(),
        "sign": sign,
        "is_quick": True,  # флаг чтобы различать в аналитике
    }
    await rabbit_client.publish(message=message)


@dataclass
class CreatePlannedChore(BaseService[PlannedChore]):
    schedule: ChoreSchedule | None
    chore: Chore
    assigned_to_user: User | None
    created_by: User
    due_date: datetime.date
    message: str
    db_session: AsyncSession

    async def process(self) -> PlannedChore:
        planned_chore = await self._create_planned_chore()
        return planned_chore

    async def _create_planned_chore(self) -> PlannedChore:
        planned_chore_dal = PlannedChoreRepository(self.db_session)
        planned_chore = PlannedChore(
            schedule_id=self.schedule.id if self.schedule is not None else None,
            chore_id=self.chore.id,
            family_id=self.chore.family_id,
            completed_by_id=None,
            assigned_to_id=self.assigned_to_user.id
            if self.assigned_to_user is not None
            else None,
            due_date=self.due_date,
            message=self.message,
            created_by=self.created_by.id,
        )
        planned_chore = await planned_chore_dal.create(planned_chore)
        return planned_chore


@dataclass
class DeletePlannedChore(BaseService[RewardTransaction | None]):
    planned_chore: PlannedChore
    db_session: AsyncSession

    async def process(self) -> RewardTransaction | None:
        if self.planned_chore.completed_by_id is None:
            await self._delete_planned_chore()
            return None
        else:
            if ENABLE_CLICKHOUSE:
                # The PlannedChore has been completed - we remove it from the statistics before deleting
                await publish_chore_completion_event(self.planned_chore, sign=-1)
            await self._soft_delete_planned_chore()
            return await self._revoke_award()

    async def _delete_planned_chore(self) -> None:
        repo = PlannedChoreRepository(self.db_session)
        await repo.hard_delete(self.planned_chore.id)

    async def _soft_delete_planned_chore(self) -> None:
        repo = PlannedChoreRepository(self.db_session)
        await repo.soft_delete(self.planned_chore.id)

    async def _revoke_award(self) -> RewardTransaction:
        service = AwardService(
            planned_chore=self.planned_chore,
            message="Отмена награды за выполнение задания",
            db_session=self.db_session,
            amount_multiplier=-1,
        )
        return await service.run_process()


@dataclass
class CompletePlannedChore(BaseService[PlannedChore]):
    planned_chore: PlannedChore
    completed_by: User
    db_session: AsyncSession

    async def process(self) -> PlannedChore:
        planned_chore = await self._complete_planned_chore()
        await self.increment_family_total_completed()
        await self.increment_user_total_completed()
        if ENABLE_CLICKHOUSE:
            await publish_chore_completion_event(planned_chore, sign=1)
        await self.send_reward()
        return planned_chore

    async def _complete_planned_chore(self) -> PlannedChore:
        repo = PlannedChoreRepository(self.db_session)
        self.planned_chore.completed_by_id = self.completed_by.id
        return await repo.update(self.planned_chore)

    async def increment_family_total_completed(self) -> None:
        repo = FamilyRepository(self.db_session)
        return await repo.increment_total_completed(self.planned_chore.family_id)

    async def increment_user_total_completed(self) -> None:
        repo = UserRepository(self.db_session)
        return await repo.increment_total_completed(self.completed_by.id)

    async def send_reward(self):
        service = AwardService(
            planned_chore=self.planned_chore,
            message="income",
            db_session=self.db_session,
        )
        await service.run_process()

    def get_validators(self):
        return [
            lambda: validate_planned_chore_is_not_completed(self.planned_chore),
            lambda: validate_date_is_not_in_past(self.planned_chore.due_date),
        ]


@dataclass
class UncompletePlannedChore(BaseService[PlannedChore]):
    planned_chore: PlannedChore
    db_session: AsyncSession

    async def process(self) -> PlannedChore:
        if ENABLE_CLICKHOUSE:
            # публикуем ДО очистки completed_by_id — нужны те же значения, что были при complete
            await publish_chore_completion_event(self.planned_chore, sign=-1)

        await self.decrement_family_total_completed()
        await self.decrement_user_total_completed()
        await self._revoke_award()
        planned_chore = await self._uncomplete_planned_chore()
        return planned_chore

    async def _uncomplete_planned_chore(self) -> PlannedChore:
        repo = PlannedChoreRepository(self.db_session)
        self.planned_chore.completed_by_id = None
        return await repo.update(self.planned_chore)

    async def decrement_family_total_completed(self) -> None:
        repo = FamilyRepository(self.db_session)
        return await repo.decrement_total_completed(self.planned_chore.family_id)

    async def decrement_user_total_completed(self) -> None:
        repo = UserRepository(self.db_session)
        return await repo.decrement_total_completed(self.planned_chore.completed_by_id)

    async def _revoke_award(self) -> RewardTransaction:
        service = AwardService(
            planned_chore=self.planned_chore,
            message="Отмена награды за выполнение задания",
            db_session=self.db_session,
            amount_multiplier=-1,
        )
        return await service.run_process()

    def get_validators(self):
        return [lambda: validate_planned_chore_is_completed(self.planned_chore)]


@dataclass
class ReschedulePlannedChore(BaseService[PlannedChore]):
    planned_chore: PlannedChore
    reschedule_due_date: datetime.date
    db_session: AsyncSession

    async def process(self) -> PlannedChore:
        return await self.reschedule_planned_chore()

    async def reschedule_planned_chore(self) -> PlannedChore:
        self.planned_chore.due_date = self.reschedule_due_date
        repo = PlannedChoreRepository(self.db_session)
        return await repo.update(self.planned_chore)

    def get_validators(self):
        return [
            lambda: validate_planned_chore_is_not_completed(self.planned_chore),
        ]


@dataclass
class UpdatePlannedChoreMessage(BaseService[PlannedChore]):
    planned_chore: PlannedChore
    message: str
    db_session: AsyncSession

    async def process(self) -> PlannedChore:
        return await self.update_planned_chore_message()

    async def update_planned_chore_message(self) -> PlannedChore:
        self.planned_chore.message = self.message
        repo = PlannedChoreRepository(self.db_session)
        return await repo.update(self.planned_chore)


UpdatePlannedChore = UpdatePlannedChoreMessage


@dataclass
class CreateChoreSchedule(BaseService[ChoreSchedule]):
    """
    Creates a new recurring chore schedule (ChoreSchedule).
    Validates recurrence frequency, bitmask / day bounds, and family membership.
    """
    chore: Chore
    assigned_to: User
    created_by: User
    frequency_type: FrequencyTypeENUM
    interval: int
    days_of_week: int | None
    day_of_month: int | None
    starts_at: datetime.date
    ends_at: datetime.date | None

    db_session: AsyncSession

    async def process(self) -> ChoreSchedule:
        schedule = await self._create_schedule()
        generator = GeneratePlannedChores(db_session=self.db_session)
        await generator.generate_for_schedule(schedule)
        return schedule

    async def _create_schedule(self) -> ChoreSchedule:
        repo = ChoreScheduleRepository(self.db_session)
        schedule = ChoreSchedule(
            chore_id=self.chore.id,
            family_id=self.chore.family_id,
            assigned_to_id=self.assigned_to.id,
            created_by=self.created_by.id,
            frequency_type=self.frequency_type,
            interval=self.interval,
            days_of_week=self.days_of_week,
            day_of_month=self.day_of_month,
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            last_generated_until=None,
            is_active=True,
        )
        return await repo.create(schedule)

    def get_validators(self):
        return [
            lambda: self._validate_interval(),
            lambda: self._validate_days_of_week(),
            lambda: self._validate_day_of_month(),
            lambda: self._validate_dates(),
            lambda: self._validate_assigned_to_family(),
        ]

    def _validate_interval(self) -> None:
        if self.interval < 1:
            raise ValueError("Interval must be at least 1")

    def _validate_days_of_week(self) -> None:
        if self.frequency_type == FrequencyTypeENUM.weekly:
            if self.days_of_week is None:
                raise ValueError("days_of_week is required for weekly frequency")
            if not (1 <= self.days_of_week <= 127):  # 0b0000001 - 0b1111111
                raise ValueError("days_of_week bitmask must be between 1 and 127")

    def _validate_day_of_month(self) -> None:
        if self.frequency_type == FrequencyTypeENUM.monthly:
            if self.day_of_month is None:
                raise ValueError("day_of_month is required for monthly frequency")
            if not (1 <= self.day_of_month <= 31):
                raise ValueError("day_of_month must be between 1 and 31")

    def _validate_dates(self) -> None:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at cannot be before starts_at")

    def _validate_assigned_to_family(self) -> None:
        if self.assigned_to.family_id != self.chore.family_id:
            raise ValueError("assigned_to user does not belong to the chore's family")


# Backward compatibility alias
CreateChoreScheduleService = CreateChoreSchedule


@dataclass
class UpdateChoreSchedule(BaseService[ChoreSchedule]):
    """
    Updates an existing recurring chore schedule and reconciles future uncompleted planned chores.
    Deletes uncompleted chores that do not match the new recurrence parameters.
    """
    schedule: ChoreSchedule
    body: ChoreScheduleUpdateSchema
    db_session: AsyncSession
    assigned_to: User | None = None

    def get_validators(self):
        return [
            lambda: self._validate_frequency_and_fields(),
            lambda: self._validate_dates(),
            lambda: self._validate_assigned_to(),
        ]

    def _validate_frequency_and_fields(self) -> None:
        target_freq = (
            self.body.frequency_type
            if self.body.frequency_type is not None
            else self.schedule.frequency_type
        )
        target_interval = (
            self.body.interval
            if self.body.interval is not None
            else self.schedule.interval
        )
        target_days = (
            self.body.days_of_week
            if self.body.days_of_week is not None
            else self.schedule.days_of_week
        )
        target_day_month = (
            self.body.day_of_month
            if self.body.day_of_month is not None
            else self.schedule.day_of_month
        )

        if target_interval < 1:
            raise ValueError("Interval must be at least 1")

        if target_freq == FrequencyTypeENUM.weekly:
            if target_days is None:
                raise ValueError("days_of_week is required for weekly frequency")
            if not (1 <= target_days <= 127):
                raise ValueError("days_of_week bitmask must be between 1 and 127")
        elif target_freq == FrequencyTypeENUM.monthly:
            if target_day_month is None:
                raise ValueError("day_of_month is required for monthly frequency")
            if not (1 <= target_day_month <= 31):
                raise ValueError("day_of_month must be between 1 and 31")

    def _validate_dates(self) -> None:
        target_starts_at = (
            self.body.starts_at
            if self.body.starts_at is not None
            else self.schedule.starts_at
        )
        target_ends_at = (
            self.body.ends_at
            if self.body.ends_at is not None
            else self.schedule.ends_at
        )
        if target_ends_at is not None and target_ends_at < target_starts_at:
            raise ValueError("ends_at cannot be before starts_at")

    def _validate_assigned_to(self) -> None:
        if self.assigned_to is not None:
            if self.assigned_to.family_id != self.schedule.family_id:
                raise ValueError(
                    "assigned_to user does not belong to the schedule's family"
                )

    async def process(self) -> ChoreSchedule:
        update_data = self.body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(self.schedule, field, value)

        if self.assigned_to is not None:
            self.schedule.assigned_to_id = self.assigned_to.id

        repo = ChoreScheduleRepository(self.db_session)
        updated_schedule = await repo.update(self.schedule)

        generator = GeneratePlannedChores(db_session=self.db_session)
        await generator.reconcile_for_schedule(updated_schedule)

        return updated_schedule


@dataclass
class DeleteChoreSchedule(BaseService[None]):
    """
    Deactivates (soft-deletes) a chore schedule and cleans up associated future uncompleted chores.
    Optionally revokes completion awards for already completed chores if specified.
    """
    schedule: ChoreSchedule
    db_session: AsyncSession
    revoke_completed_awards: bool = False

    async def process(self) -> None:
        repo = ChoreScheduleRepository(self.db_session)
        await repo.soft_delete(self.schedule.id)
        self.schedule.is_active = False

        # Delete / cancel future uncompleted planned chores
        planned_chore_repo = PlannedChoreRepository(self.db_session)
        query = select(PlannedChore).where(
            PlannedChore.schedule_id == self.schedule.id,
            PlannedChore.is_active.is_(True),
        )
        result = await self.db_session.execute(query)
        planned_chores = list(result.scalars().all())

        for planned_chore in planned_chores:
            if planned_chore.completed_by_id is None:
                await planned_chore_repo.hard_delete(planned_chore.id)
            elif self.revoke_completed_awards:
                delete_service = DeletePlannedChore(
                    planned_chore=planned_chore,
                    db_session=self.db_session,
                )
                await delete_service.run_process()


@dataclass
class GeneratePlannedChores(BaseService[int]):
    """
    Generates planned chores ahead for all active recurring chore schedules.
    Maintains a rolling horizon (default: 3 weeks) idempotently.
    """
    db_session: AsyncSession
    horizon_weeks: int = 3

    async def process(self) -> int:
        schedule_repo = ChoreScheduleRepository(self.db_session)
        schedules = await schedule_repo.get_active()

        today = datetime.date.today()
        horizon_end = today + datetime.timedelta(weeks=self.horizon_weeks)

        total_generated = 0
        for schedule in schedules:
            generated = await self.generate_for_schedule(
                schedule=schedule,
                generate_until=horizon_end,
            )
            total_generated += len(generated)

        await self.db_session.flush()
        return total_generated

    async def generate_for_schedule(
        self,
        schedule: ChoreSchedule,
        generate_until: datetime.date | None = None,
    ) -> list[PlannedChore]:
        """
        Generates upcoming PlannedChore instances for a single schedule from its last generated date.
        Uses idempotency checks to prevent duplicate chores on the same date.
        """
        if not schedule.is_active:
            return []

        today = datetime.date.today()
        if generate_until is None:
            generate_until = today + datetime.timedelta(weeks=self.horizon_weeks)

        if schedule.ends_at is not None:
            generate_until = min(generate_until, schedule.ends_at)

        # Window calculation
        start_date = schedule.starts_at
        if schedule.last_generated_until is not None:
            start_date = max(
                start_date,
                schedule.last_generated_until + datetime.timedelta(days=1),
            )

        if start_date > generate_until:
            return []

        # Strict idempotency: prefetch existing PlannedChore due_dates for this schedule
        existing_query = select(PlannedChore.due_date).where(
            PlannedChore.schedule_id == schedule.id,
            PlannedChore.is_active.is_(True),
            PlannedChore.due_date >= start_date,
            PlannedChore.due_date <= generate_until,
        )
        result = await self.db_session.execute(existing_query)
        existing_due_dates = set(result.scalars().all())

        new_chores: list[PlannedChore] = []
        current = start_date

        while current <= generate_until:
            if self._matches_schedule(schedule, current):
                if current not in existing_due_dates:
                    new_chore = PlannedChore(
                        schedule_id=schedule.id,
                        chore_id=schedule.chore_id,
                        family_id=schedule.family_id,
                        completed_by_id=None,
                        assigned_to_id=schedule.assigned_to_id,
                        due_date=current,
                        message="",
                        created_by=schedule.created_by,
                        is_active=True,
                    )
                    self.db_session.add(new_chore)
                    new_chores.append(new_chore)
                    existing_due_dates.add(current)

            current += datetime.timedelta(days=1)

        # Advance last_generated_until to the end of calculated horizon
        if (
            schedule.last_generated_until is None
            or generate_until > schedule.last_generated_until
        ):
            schedule.last_generated_until = generate_until
            schedule_repo = ChoreScheduleRepository(self.db_session)
            await schedule_repo.update(schedule)

        return new_chores

    async def reconcile_for_schedule(
        self,
        schedule: ChoreSchedule,
        from_date: datetime.date | None = None,
        generate_until: datetime.date | None = None,
    ) -> list[PlannedChore]:
        """
        Reconciles planned chores after a schedule modification.
        - Deletes future uncompleted chores that no longer match the new recurrence rules.
        - Preserves completed chores and their rewards.
        - Generates missing matching chores up to the horizon limit.
        - Updates schedule.last_generated_until.
        """
        today = datetime.date.today()
        if from_date is None:
            from_date = today

        planned_chore_repo = PlannedChoreRepository(self.db_session)

        # 1. If schedule is inactive, delete all uncompleted future chores
        if not schedule.is_active:
            query = select(PlannedChore).where(
                PlannedChore.schedule_id == schedule.id,
                PlannedChore.is_active.is_(True),
                PlannedChore.due_date >= from_date,
            )
            result = await self.db_session.execute(query)
            existing_chores = list(result.scalars().all())
            for chore in existing_chores:
                if chore.completed_by_id is None:
                    await planned_chore_repo.hard_delete(chore.id)
            await self.db_session.flush()
            return []

        # 2. Determine generation horizon
        if generate_until is None:
            generate_until = today + datetime.timedelta(weeks=self.horizon_weeks)

        if schedule.ends_at is not None:
            generate_until = min(generate_until, schedule.ends_at)

        # 3. Query all active planned chores related to this schedule/chore from from_date onwards
        query = select(PlannedChore).where(
            (PlannedChore.schedule_id == schedule.id)
            | (
                (PlannedChore.chore_id == schedule.chore_id)
                & (PlannedChore.family_id == schedule.family_id)
            ),
            PlannedChore.is_active.is_(True),
            PlannedChore.due_date >= from_date,
        )
        result = await self.db_session.execute(query)
        existing_chores = list(result.scalars().all())

        existing_due_dates: set[datetime.date] = set()

        for chore in existing_chores:
            if chore.schedule_id != schedule.id:
                # Standalone/manual chore for the same chore: preserve it and don't duplicate on this date
                existing_due_dates.add(chore.due_date)
                continue

            if chore.completed_by_id is not None:
                # Completed chore: never delete completed chores
                existing_due_dates.add(chore.due_date)
                continue

            # Check if this uncompleted chore still satisfies the updated schedule
            should_keep = (
                chore.due_date >= schedule.starts_at
                and (schedule.ends_at is None or chore.due_date <= schedule.ends_at)
                and chore.due_date <= generate_until
                and self._matches_schedule(schedule, chore.due_date)
            )

            if should_keep:
                # Synchronize assigned user if schedule was reassigned
                if (
                    schedule.assigned_to_id is not None
                    and chore.assigned_to_id != schedule.assigned_to_id
                ):
                    chore.assigned_to_id = schedule.assigned_to_id
                existing_due_dates.add(chore.due_date)
            else:
                # Chore does not match the updated schedule -> remove it!
                await planned_chore_repo.hard_delete(chore.id)

        # 4. Generate missing chores up to generate_until
        start_date = max(from_date, schedule.starts_at)
        new_chores: list[PlannedChore] = []

        if start_date <= generate_until:
            current = start_date
            while current <= generate_until:
                if self._matches_schedule(schedule, current):
                    if current not in existing_due_dates:
                        new_chore = PlannedChore(
                            schedule_id=schedule.id,
                            chore_id=schedule.chore_id,
                            family_id=schedule.family_id,
                            completed_by_id=None,
                            assigned_to_id=schedule.assigned_to_id,
                            due_date=current,
                            message="",
                            created_by=schedule.created_by,
                            is_active=True,
                        )
                        self.db_session.add(new_chore)
                        new_chores.append(new_chore)
                        existing_due_dates.add(current)
                current += datetime.timedelta(days=1)

        # 5. Advance/reset last_generated_until
        schedule.last_generated_until = generate_until
        schedule_repo = ChoreScheduleRepository(self.db_session)
        await schedule_repo.update(schedule)
        await self.db_session.flush()

        return new_chores

    def _matches_schedule(
        self,
        schedule: ChoreSchedule,
        date: datetime.date,
    ) -> bool:
        if date < schedule.starts_at:
            return False

        if schedule.ends_at is not None and date > schedule.ends_at:
            return False

        if schedule.frequency_type == FrequencyTypeENUM.daily:
            return self._matches_daily(schedule, date)

        if schedule.frequency_type == FrequencyTypeENUM.weekly:
            return self._matches_weekly(schedule, date)

        if schedule.frequency_type == FrequencyTypeENUM.monthly:
            return self._matches_monthly(schedule, date)

        return False

    def _matches_daily(
        self,
        schedule: ChoreSchedule,
        date: datetime.date,
    ) -> bool:
        delta = (date - schedule.starts_at).days
        return delta % schedule.interval == 0

    def _matches_weekly(
        self,
        schedule: ChoreSchedule,
        date: datetime.date,
    ) -> bool:
        if schedule.days_of_week is None:
            return False

        starts_monday = schedule.starts_at - datetime.timedelta(
            days=schedule.starts_at.weekday()
        )
        current_monday = date - datetime.timedelta(days=date.weekday())
        weeks_diff = (current_monday - starts_monday).days // 7

        if weeks_diff % schedule.interval != 0:
            return False

        weekday = date.weekday()  # Monday = 0, Tuesday = 1, ... Sunday = 6
        return bool(schedule.days_of_week & (1 << weekday))

    def _matches_monthly(
        self,
        schedule: ChoreSchedule,
        date: datetime.date,
    ) -> bool:
        if schedule.day_of_month is None:
            return False

        months_diff = (
            (date.year - schedule.starts_at.year) * 12
            + date.month
            - schedule.starts_at.month
        )

        if months_diff % schedule.interval != 0:
            return False

        last_day_of_month = calendar.monthrange(date.year, date.month)[1]
        target_day = min(schedule.day_of_month, last_day_of_month)

        return date.day == target_day


@dataclass
class CreateQuickPlannedChore(BaseService[QuickPlannedChore]):
    body: QuickPlannedChoreCreateSchema
    current_user: User
    assigned_to_user: User | None
    db_session: AsyncSession

    async def process(self) -> QuickPlannedChore:
        repo = QuickPlannedChoreRepository(self.db_session)
        obj = QuickPlannedChore(
            name=self.body.name,
            description=self.body.description,
            icon=self.body.icon,
            icon_color=self.body.icon_color,
            icon_bg=self.body.icon_bg,
            valuation=self.body.valuation,
            family_id=self.current_user.family_id,
            assigned_to_id=self.assigned_to_user.id if self.assigned_to_user else None,
            due_date=self.body.due_date,
            message=self.body.message,
            created_by=self.current_user.id,
            completed_by_id=None,
            is_active=True,
        )
        return await repo.create(obj)


@dataclass
class CompleteQuickPlannedChore(BaseService[QuickPlannedChore]):
    quick_planned_chore: QuickPlannedChore
    current_user: User
    db_session: AsyncSession

    async def process(self) -> QuickPlannedChore:
        quick_planned_chore = await self._complete_quick_planned_chore()
        await self.increment_family_total_completed()
        await self.increment_user_total_completed()
        if ENABLE_CLICKHOUSE:
            await publish_quick_chore_completion_event(quick_planned_chore, sign=1)
        await self.send_reward()
        return quick_planned_chore

    async def _complete_quick_planned_chore(self) -> QuickPlannedChore:
        repo = QuickPlannedChoreRepository(self.db_session)
        self.quick_planned_chore.completed_by_id = self.current_user.id
        self.quick_planned_chore = await repo.update(self.quick_planned_chore)
        return self.quick_planned_chore

    async def increment_family_total_completed(self) -> None:
        await FamilyRepository(self.db_session).increment_total_completed(
            self.quick_planned_chore.family_id
        )

    async def increment_user_total_completed(self) -> None:
        await UserRepository(self.db_session).increment_total_completed(
            self.current_user.id  # ← было self.quick_planned_chore.id
        )

    async def send_reward(self):
        await QuickAwardService(
            quick_chore=self.quick_planned_chore,
            message="income",
            db_session=self.db_session,
        ).run_process()

    def get_validators(self):
        return [
            lambda: validate_quick_planned_chore_is_not_completed(
                self.quick_planned_chore
            ),
        ]


@dataclass
class UncompleteQuickPlannedChore(BaseService[QuickPlannedChore]):
    quick_planned_chore: QuickPlannedChore
    db_session: AsyncSession

    async def process(self) -> QuickPlannedChore:
        if ENABLE_CLICKHOUSE:
            await publish_quick_chore_completion_event(
                self.quick_planned_chore, sign=-1
            )
        await self.decrement_family_total_completed()
        await self.decrement_user_total_completed()
        await self._revoke_award()
        return await self._uncomplete_quick_planned_chore()

    async def _uncomplete_quick_planned_chore(self) -> QuickPlannedChore:
        repo = QuickPlannedChoreRepository(self.db_session)
        self.quick_planned_chore.completed_by_id = None
        return await repo.update(self.quick_planned_chore)

    async def decrement_family_total_completed(self) -> None:
        repo = FamilyRepository(self.db_session)
        return await repo.decrement_total_completed(self.quick_planned_chore.family_id)

    async def decrement_user_total_completed(self) -> None:
        repo = UserRepository(self.db_session)
        return await repo.decrement_total_completed(
            self.quick_planned_chore.completed_by_id
        )

    async def _revoke_award(self) -> RewardTransaction:
        service = QuickAwardService(
            quick_chore=self.quick_planned_chore,
            message="Отмена награды за выполнение задания",
            db_session=self.db_session,
            amount_multiplier=-1,
        )
        return await service.run_process()

    def get_validators(self):
        return [
            lambda: validate_quick_planned_chore_is_completed(self.quick_planned_chore)
        ]


@dataclass
class UpdateQuickPlannedChore(BaseService[QuickPlannedChore]):
    quick_planned_chore_id: UUID
    body: QuickPlannedChoreUpdateSchema
    current_user: User
    db_session: AsyncSession

    async def process(self) -> QuickPlannedChore:
        repo = QuickPlannedChoreRepository(self.db_session)
        obj = await repo.get_by_id(self.quick_planned_chore_id)

        for field, value in self.body.model_dump(exclude_none=True).items():
            setattr(obj, field, value)

        return await repo.update(obj)


@dataclass
class DeleteQuickPlannedChore(BaseService[None]):
    quick_planned_chore_id: UUID
    db_session: AsyncSession

    async def process(self) -> None:
        repo = QuickPlannedChoreRepository(self.db_session)
        obj = await repo.get_by_id(self.quick_planned_chore_id)

        if obj.completed_by_id is not None:
            await AwardService(
                planned_chore=obj,
                message="Отмена награды за выполнение задания",
                db_session=self.db_session,
                amount_multiplier=-1,
            ).run_process()

            await FamilyRepository(self.db_session).decrement_total_completed(
                obj.family_id
            )
            await UserRepository(self.db_session).decrement_total_completed(
                obj.completed_by_id
            )

        await repo.soft_delete(self.quick_planned_chore_id)
