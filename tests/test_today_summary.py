import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from families.models import Event
from families.schemas import (
    EventResponseSchema,
    TodayChoresSummarySchema,
    TodayMealsSummarySchema,
    TodaySummaryResponseSchema,
)
from families.today_summary_service import GetTodaySummaryService
from meals.models import GroceryItem, PlannedMeal
from meals.schemas import GroceryItemResponseSchema, PlannedMealResponseSchema
from users.models import User


@pytest.fixture
def test_date() -> datetime.date:
    return datetime.date(2026, 10, 9)


async def test_get_today_summary_service_empty(mock_db_session: AsyncMock, test_date: datetime.date):
    family_id = uuid.uuid4()
    service = GetTodaySummaryService(
        family_id=family_id,
        target_date=test_date,
        unbought_only=True,
        db_session=mock_db_session,
    )

    summary = await service.run_process()

    assert summary.date == test_date
    assert summary.chores.total == 0
    assert summary.chores.active == 0
    assert summary.chores.completed == 0
    assert summary.chores_count == 0
    assert summary.groceries == []
    assert summary.groceries_count == 0
    assert summary.event is None
    assert summary.events == []
    assert summary.meals.breakfast == []
    assert summary.meals.lunch == []
    assert summary.meals.dinner == []
    assert summary.meals.snack == []
    assert summary.meals.total_count == 0


async def test_get_today_summary_service_populated(mock_db_session: AsyncMock, test_date: datetime.date):
    family_id = uuid.uuid4()
    user_id = uuid.uuid4()

    event = Event(
        id=uuid.uuid4(),
        name="Family Dinner Party",
        description="Evening party",
        date=datetime.datetime(2026, 10, 9, 19, 0),
        created_at=datetime.datetime(2026, 10, 1, 10, 0),
        icon="party",
        icon_color="#ffffff",
        icon_bg="#FF5722",
        family_id=family_id,
    )

    grocery1 = GroceryItem(
        id=uuid.uuid4(),
        name="Milk",
        amount=1.0,
        unit="l",
        category="dairy",
        is_bought=False,
        is_active=True,
        family_id=family_id,
        created_at=datetime.datetime(2026, 10, 9, 8, 0),
    )

    breakfast_meal = PlannedMeal(
        id=uuid.uuid4(),
        family_id=family_id,
        date=test_date,
        slot="breakfast",
        title="Oatmeal with berries",
        prep_time_minutes=15,
        recipe_id=None,
        assigned_cook_id=user_id,
        servings=4,
        note=None,
        is_completed=False,
        completed_by_id=None,
        created_by_id=user_id,
        is_active=True,
        created_at=datetime.datetime(2026, 10, 9, 7, 0),
    )
    breakfast_meal.cook = None
    breakfast_meal.completed_by = None
    breakfast_meal.recipe = None

    dinner_meal = PlannedMeal(
        id=uuid.uuid4(),
        family_id=family_id,
        date=test_date,
        slot="dinner",
        title="Salmon and rice",
        prep_time_minutes=30,
        recipe_id=None,
        assigned_cook_id=user_id,
        servings=4,
        note=None,
        is_completed=True,
        completed_by_id=user_id,
        created_by_id=user_id,
        is_active=True,
        created_at=datetime.datetime(2026, 10, 9, 12, 0),
    )
    dinner_meal.cook = None
    dinner_meal.completed_by = None
    dinner_meal.recipe = None

    service = GetTodaySummaryService(
        family_id=family_id,
        target_date=test_date,
        unbought_only=True,
        db_session=mock_db_session,
    )

    with (
        patch.object(
            service,
            "_get_chores_summary",
            new_callable=AsyncMock,
            return_value=TodayChoresSummarySchema(total=5, active=3, completed=2),
        ),
        patch.object(
            service,
            "_get_groceries",
            new_callable=AsyncMock,
            return_value=[GroceryItemResponseSchema.model_validate(grocery1)],
        ),
        patch.object(
            service,
            "_get_events",
            new_callable=AsyncMock,
            return_value=(
                EventResponseSchema.model_validate(event),
                [EventResponseSchema.model_validate(event)],
            ),
        ),
        patch.object(
            service,
            "_get_meals_summary",
            new_callable=AsyncMock,
            return_value=TodayMealsSummarySchema(
                breakfast=[PlannedMealResponseSchema.model_validate(breakfast_meal)],
                lunch=[],
                dinner=[PlannedMealResponseSchema.model_validate(dinner_meal)],
                snack=[],
                total_count=2,
            ),
        ),
    ):
        result = await service.run_process()

        assert result.chores.total == 5
        assert result.chores.active == 3
        assert result.chores.completed == 2
        assert result.chores_count == 5
        assert len(result.groceries) == 1
        assert result.groceries[0].name == "Milk"
        assert result.groceries_count == 1
        assert result.event is not None
        assert result.event.name == "Family Dinner Party"
        assert len(result.events) == 1
        assert len(result.meals.breakfast) == 1
        assert result.meals.breakfast[0].title == "Oatmeal with berries"
        assert len(result.meals.dinner) == 1
        assert result.meals.total_count == 2


async def test_today_summary_endpoint(async_client: AsyncClient, sample_user: User):
    sample_summary = TodaySummaryResponseSchema(
        date=datetime.date(2026, 10, 9),
        chores=TodayChoresSummarySchema(total=4, active=2, completed=2),
        chores_count=4,
        groceries=[
            GroceryItemResponseSchema(
                id=uuid.uuid4(),
                family_id=sample_user.family_id,
                name="Apples",
                amount=1.5,
                unit="kg",
                category="fruits",
                is_bought=False,
                added_from_recipe=None,
                created_at=datetime.datetime(2026, 10, 9, 9, 0),
            )
        ],
        groceries_count=1,
        event=None,
        events=[],
        meals=TodayMealsSummarySchema(
            breakfast=[],
            lunch=[],
            dinner=[],
            snack=[],
            total_count=0,
        ),
    )

    with patch(
        "families.today_summary_service.GetTodaySummaryService.run_process",
        new_callable=AsyncMock,
    ) as mock_service:
        mock_service.return_value = sample_summary

        # 1. Test /api/families/today-summary
        response = await async_client.get("/api/families/today-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-10-09"
        assert data["chores"]["total"] == 4
        assert data["chores"]["active"] == 2
        assert data["chores"]["completed"] == 2
        assert data["chores_count"] == 4
        assert len(data["groceries"]) == 1
        assert data["groceries"][0]["name"] == "Apples"
        assert data["groceries_count"] == 1
        assert data["event"] is None
        assert data["meals"]["total_count"] == 0

        # 2. Test /api/families/today
        response2 = await async_client.get("/api/families/today?date=2026-10-09")
        assert response2.status_code == 200
        assert response2.json()["date"] == "2026-10-09"

        # 3. Test /api/today-summary
        response3 = await async_client.get("/api/today-summary")
        assert response3.status_code == 200
        assert response3.json()["chores_count"] == 4

        # 4. Test /api/today
        response4 = await async_client.get("/api/today")
        assert response4.status_code == 200
        assert response4.json()["chores_count"] == 4
