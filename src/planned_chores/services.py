from dataclasses import dataclass
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import ENABLE_CLICKHOUSE
from core.services import BaseService
from database_connection import rabbit_client
from chores.models import Chore
from families.models import Family
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.repository import ChoreScheduleRepository, PlannedChoreRepository
from core.enums import FrequencyTypeENUM
from core.validators import (
    validate_date_is_not_in_past,
    validate_planned_chore_is_completed,
    validate_planned_chore_is_not_completed,
)
from users.models import User
from wallets.models import RewardTransaction
from wallets.services import AwardService


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
        if ENABLE_CLICKHOUSE:
            await publish_chore_completion_event(planned_chore, sign=1)
        await self.send_reward()
        return planned_chore

    async def _complete_planned_chore(self) -> PlannedChore:
        repo = PlannedChoreRepository(self.db_session)
        self.planned_chore.completed_by_id = self.completed_by.id
        return await repo.update(self.planned_chore)

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

        await self._revoke_award()
        planned_chore = await self._uncomplete_planned_chore()
        return planned_chore

    async def _uncomplete_planned_chore(self) -> PlannedChore:
        repo = PlannedChoreRepository(self.db_session)
        self.planned_chore.completed_by_id = None
        return await repo.update(self.planned_chore)

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
            lambda: validate_date_is_not_in_past(self.reschedule_due_date),
            lambda: validate_planned_chore_is_not_completed(self.planned_chore),
        ]


@dataclass
class CreateChoreScheduleService(BaseService[ChoreSchedule]):
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
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.starts_at < datetime.date.today():
            raise ValueError("starts_at cannot be in the past")

    def _validate_assigned_to_family(self) -> None:
        if self.assigned_to.family_id != self.chore.family_id:
            raise ValueError("assigned_to user does not belong to the chore's family")
