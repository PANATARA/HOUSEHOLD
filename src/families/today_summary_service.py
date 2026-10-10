import datetime
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.services import BaseService
from families.models import Event
from families.schemas import (
    EventResponseSchema,
    TodayChoresSummarySchema,
    TodayMealsSummarySchema,
    TodaySummaryResponseSchema,
)
from meals.models import GroceryItem, PlannedMeal
from meals.schemas import GroceryItemResponseSchema, PlannedMealResponseSchema
from planned_chores.models import PlannedChore, QuickPlannedChore


@dataclass
class GetTodaySummaryService(BaseService[TodaySummaryResponseSchema]):
    """Service to fetch a complete daily summary for a family."""

    family_id: UUID
    target_date: datetime.date
    unbought_only: bool
    db_session: AsyncSession

    async def process(self) -> TodaySummaryResponseSchema:
        chores_summary = await self._get_chores_summary()
        groceries = await self._get_groceries()
        event, events = await self._get_events()
        meals_summary = await self._get_meals_summary()

        return TodaySummaryResponseSchema(
            date=self.target_date,
            chores=chores_summary,
            chores_count=chores_summary.total,
            groceries=groceries,
            groceries_count=len(groceries),
            event=event,
            events=events,
            meals=meals_summary,
        )

    async def _get_chores_summary(self) -> TodayChoresSummarySchema:
        # 1. Planned chores
        planned_query = select(
            func.count(PlannedChore.id).label("total"),
            func.coalesce(
                func.sum(
                    case((PlannedChore.completed_by_id.is_(None), 1), else_=0)
                ),
                0,
            ).label("active"),
            func.coalesce(
                func.sum(
                    case((PlannedChore.completed_by_id.isnot(None), 1), else_=0)
                ),
                0,
            ).label("completed"),
        ).where(
            PlannedChore.family_id == self.family_id,
            PlannedChore.is_active.is_(True),
            PlannedChore.due_date == self.target_date,
        )
        planned_row = (await self.db_session.execute(planned_query)).mappings().first()
        p_total = int(planned_row["total"] or 0) if planned_row else 0
        p_active = int(planned_row["active"] or 0) if planned_row else 0
        p_completed = int(planned_row["completed"] or 0) if planned_row else 0

        # 2. Quick planned chores
        quick_query = select(
            func.count(QuickPlannedChore.id).label("total"),
            func.coalesce(
                func.sum(
                    case(
                        (QuickPlannedChore.completed_by_id.is_(None), 1), else_=0
                    )
                ),
                0,
            ).label("active"),
            func.coalesce(
                func.sum(
                    case(
                        (QuickPlannedChore.completed_by_id.isnot(None), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("completed"),
        ).where(
            QuickPlannedChore.family_id == self.family_id,
            QuickPlannedChore.is_active.is_(True),
            QuickPlannedChore.due_date == self.target_date,
        )
        quick_row = (await self.db_session.execute(quick_query)).mappings().first()
        q_total = int(quick_row["total"] or 0) if quick_row else 0
        q_active = int(quick_row["active"] or 0) if quick_row else 0
        q_completed = int(quick_row["completed"] or 0) if quick_row else 0

        return TodayChoresSummarySchema(
            total=p_total + q_total,
            active=p_active + q_active,
            completed=p_completed + q_completed,
        )

    async def _get_groceries(self) -> list[GroceryItemResponseSchema]:
        conditions = [
            GroceryItem.family_id == self.family_id,
            GroceryItem.is_active.is_(True),
        ]
        if self.unbought_only:
            conditions.append(GroceryItem.is_bought.is_(False))

        query = (
            select(GroceryItem)
            .where(*conditions)
            .order_by(
                GroceryItem.is_bought.asc(),
                GroceryItem.created_at.desc(),
            )
        )
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        return [GroceryItemResponseSchema.model_validate(item) for item in items]

    async def _get_events(
        self,
    ) -> tuple[EventResponseSchema | None, list[EventResponseSchema]]:
        start_of_day = datetime.datetime.combine(self.target_date, datetime.time.min)
        end_of_day = datetime.datetime.combine(self.target_date, datetime.time.max)

        query = (
            select(Event)
            .where(
                Event.family_id == self.family_id,
                Event.date >= start_of_day,
                Event.date <= end_of_day,
            )
            .order_by(Event.date.asc())
        )
        result = await self.db_session.execute(query)
        events_list = [
            EventResponseSchema.model_validate(e) for e in result.scalars().all()
        ]
        primary_event = events_list[0] if events_list else None
        return primary_event, events_list

    async def _get_meals_summary(self) -> TodayMealsSummarySchema:
        query = (
            select(PlannedMeal)
            .where(
                PlannedMeal.family_id == self.family_id,
                PlannedMeal.date == self.target_date,
                PlannedMeal.is_active.is_(True),
            )
            .options(
                selectinload(PlannedMeal.cook),
                selectinload(PlannedMeal.completed_by),
                selectinload(PlannedMeal.recipe),
            )
            .order_by(PlannedMeal.date.asc(), PlannedMeal.created_at.asc())
        )
        result = await self.db_session.execute(query)
        meals = result.scalars().all()

        breakfast: list[PlannedMealResponseSchema] = []
        lunch: list[PlannedMealResponseSchema] = []
        dinner: list[PlannedMealResponseSchema] = []
        snack: list[PlannedMealResponseSchema] = []

        for m in meals:
            schema = PlannedMealResponseSchema.model_validate(m)
            slot = (m.slot or "").lower().strip()
            if slot == "breakfast":
                breakfast.append(schema)
            elif slot == "lunch":
                lunch.append(schema)
            elif slot == "dinner":
                dinner.append(schema)
            elif slot == "snack":
                snack.append(schema)
            else:
                snack.append(schema)

        return TodayMealsSummarySchema(
            breakfast=breakfast,
            lunch=lunch,
            dinner=dinner,
            snack=snack,
            total_count=len(meals),
        )
