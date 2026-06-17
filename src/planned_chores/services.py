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
from core.enums import FrequencyTypeENUM, StatusConfirmENUM
from core.validators import (
    validate_date_is_not_in_past,
    validate_planned_chore_is_changable,
)
from users.models import User
from wallets.models import RewardTransaction
from wallets.services import AwardService


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
            status=StatusConfirmENUM.awaits,
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
            await self.rabbit_publish()
        await self.send_reward()
        return planned_chore

    async def _complete_planned_chore(self) -> PlannedChore:
        repo = PlannedChoreRepository(self.db_session)
        self.planned_chore.status = StatusConfirmENUM.approved
        self.planned_chore.completed_by_id = self.completed_by.id
        return await repo.update(self.planned_chore)

    async def rabbit_publish(self):
        message = {
            "id": str(self.planned_chore.id),
            "chore_id": str(self.planned_chore.chore_id),
            "family_id": str(self.planned_chore.family_id),
            "completed_by_id": str(self.planned_chore.completed_by_id),
            "assigned_to_id": str(self.planned_chore.assigned_to_id),
            "due_date": self.planned_chore.due_date.isoformat(),
        }
        await rabbit_client.publish(message=message)

    async def send_reward(self):
        service = AwardService(
            planned_chore=self.planned_chore,
            message="income",
            db_session=self.db_session,
        )
        await service.run_process()

    def get_validators(self):
        return [lambda: validate_planned_chore_is_changable(self.planned_chore)]


@dataclass
class ReschedulePlannedChore:
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
            lambda: validate_planned_chore_is_changable(self.planned_chore),
            lambda: validate_date_is_not_in_past(self.reschedule_due_date),
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
