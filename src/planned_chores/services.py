from dataclasses import dataclass
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import ENABLE_CLICKHOUSE
from core.services import BaseService
from database_connection import rabbit_client
from chores.models import Chore
from families.models import Family
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.repository import PlannedChoreRepository
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

        planned_chore = await self._uncomplete_planned_chore()
        await self._revoke_award()
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
class CreateChoreSchedule:
    chore: Chore
    family: Family
    assigned_to_id: User
    created_by: User
    frequency_type: FrequencyTypeENUM  # Recurrence type: daily / weekly / monthly
    interval: int  # Repeat interval (e.g. every 2 days, every 3 weeks)
    days_of_week: int | None  # Weekday bitmask for weekly recurrence
    day_of_month: int | None  # Day of month for monthly recurrence
    starts_at: datetime.date  # Recurrence active period
    ends_at: datetime.date | None  # Recurrence active period
    last_generated_until: (
        datetime.date | None
    )  # Last date for which instances were generated

    async def process(self):
        pass

    async def _celery_work(self):
        pass
