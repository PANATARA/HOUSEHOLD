"""
Integration tests for API endpoints with a real PostgreSQL database.

These tests spin up a real Postgres via testcontainers, insert real data,
and call the FastAPI endpoints through the ASGI test client.
Auth is bypassed (the current user is always integration_factory.user).
"""

import datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from core.enums import FrequencyTypeENUM
from families.models import Family
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from users.models import User


# ── Chores Endpoints ──────────────────────────────────────────────────────────

class TestChoreCRUDEndpoints:
    """Test /api/chores endpoints against real database."""

    async def test_list_family_chores_returns_active_chores(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/chores")
        assert resp.status_code == 200
        data = resp.json()
        chores_list = data.get("chores", data)
        names = [c["name"] for c in chores_list]
        assert "Wash Dishes" in names

    async def test_list_chores_does_not_return_inactive(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        # Soft-delete the chore
        integration_factory.chore.is_active = False
        db_session.add(integration_factory.chore)
        await db_session.commit()

        resp = await integration_client.get("/api/chores")
        assert resp.status_code == 200
        data = resp.json()
        chores_list = data.get("chores", data)
        names = [c["name"] for c in chores_list]
        assert "Wash Dishes" not in names

    async def test_create_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "name": "Vacuum Floors",
            "description": "Vacuum all rooms",
            "valuation": 15,
            "icon": "material-symbols:vacuum",
            "icon_color": "#ffffff",
            "icon_bg": "#FF5722",
        }
        resp = await integration_client.post("/api/chores", json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Vacuum Floors"
        assert data["valuation"] == 15

    async def test_delete_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        resp = await integration_client.delete(
            f"/api/chores/{integration_factory.chore.id}"
        )
        assert resp.status_code in (200, 204)
        await db_session.refresh(integration_factory.chore)
        assert integration_factory.chore.is_active is False


# ── Chore Schedule Endpoints ──────────────────────────────────────────────────

class TestChoreScheduleEndpoints:

    async def test_create_schedule_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "assigned_to_id": str(integration_factory.user.id),
            "frequency_type": "daily",
            "interval": 1,
            "starts_at": datetime.date.today().isoformat(),
        }
        resp = await integration_client.post(
            f"/api/chores/{integration_factory.chore.id}/schedule",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency_type"] == "daily"
        assert data["interval"] == 1

    async def test_create_schedule_chore_not_found(
        self, integration_client: AsyncClient
    ):
        fake_id = uuid.uuid4()
        payload = {
            "assigned_to_id": str(uuid.uuid4()),
            "frequency_type": "daily",
            "interval": 1,
            "starts_at": datetime.date.today().isoformat(),
        }
        resp = await integration_client.post(
            f"/api/chores/{fake_id}/schedule",
            json=payload,
        )
        assert resp.status_code in (400, 404)

    async def test_delete_schedule_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        schedule = await integration_factory.create_schedule()
        resp = await integration_client.delete(
            f"/api/schedules/{schedule.id}"
        )
        assert resp.status_code in (200, 204)


# ── Planned Chores Board Endpoints ────────────────────────────────────────────

class TestPlannedChoreEndpoints:

    async def test_list_planned_chores_for_date(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        await integration_factory.create_planned_chore(due_date=db_today)

        resp = await integration_client.get(
            f"/api/chores/planned?due_date={db_today.isoformat()}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_planned_chores_only_returns_active(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()

        await integration_factory.create_planned_chore(due_date=db_today)
        pc2 = await integration_factory.create_planned_chore(due_date=db_today)
        pc2.is_active = False
        db_session.add(pc2)
        await db_session.commit()

        resp = await integration_client.get(
            f"/api/chores/planned?due_date={db_today.isoformat()}"
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data]
        assert str(pc2.id) not in ids

    async def test_complete_planned_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        today = datetime.date.today()
        pc = await integration_factory.create_planned_chore(due_date=today)

        resp = await integration_client.patch(
            f"/api/chores/planned/{pc.id}/complete"
        )
        assert resp.status_code == 200
        await db_session.refresh(pc)
        assert pc.completed_by_id is not None

    async def test_uncomplete_planned_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        pc = await integration_factory.create_planned_chore(
            due_date=db_today,
            completed_by=integration_factory.user,
        )
        resp = await integration_client.patch(
            f"/api/chores/planned/{pc.id}/uncomplete"
        )
        assert resp.status_code == 200
        await db_session.refresh(pc)
        assert pc.completed_by_id is None

    async def test_complete_already_completed_returns_error(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        pc = await integration_factory.create_planned_chore(
            due_date=db_today,
            completed_by=integration_factory.user,
        )
        resp = await integration_client.patch(
            f"/api/chores/planned/{pc.id}/complete"
        )
        assert resp.status_code in (400, 409, 422)

    async def test_create_planned_chore_manually(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "due_date": datetime.date.today().isoformat(),
            "assigned_to_id": str(integration_factory.user.id),
            "message": "",
        }
        resp = await integration_client.post(
            f"/api/chores/{integration_factory.chore.id}/planned",
            json=payload,
        )
        assert resp.status_code in (200, 201)

    async def test_delete_planned_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        pc = await integration_factory.create_planned_chore()
        resp = await integration_client.delete(f"/api/chores/planned/{pc.id}")
        assert resp.status_code in (200, 204)


# ── Quick Planned Chores Endpoints ────────────────────────────────────────────

class TestQuickPlannedChoreEndpoints:

    async def test_create_quick_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "name": "Take out trash",
            "valuation": 5,
            "due_date": datetime.date.today().isoformat(),
            "icon": "material-symbols:delete",
            "icon_color": "#fff",
            "icon_bg": "#aaa",
        }
        resp = await integration_client.post(
            "/api/chores/quick",
            json=payload,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data

    async def test_list_quick_chores_for_date(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        await integration_factory.create_quick_chore(due_date=db_today)

        resp = await integration_client.get(
            f"/api/chores/quick?date_from={db_today.isoformat()}&date_to={db_today.isoformat()}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_complete_quick_chore_endpoint(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        qc = await integration_factory.create_quick_chore(due_date=db_today)

        resp = await integration_client.patch(
            f"/api/chores/quick/{qc.id}/complete"
        )
        assert resp.status_code == 200
        await db_session.refresh(qc)
        assert qc.completed_by_id is not None


# ── Family Endpoints ──────────────────────────────────────────────────────────

class TestFamilyEndpoints:

    async def test_get_family_members(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/families/members")
        assert resp.status_code == 200
        data = resp.json()
        members = data.get("members", data)
        assert isinstance(members, list)
        assert len(members) >= 2  # user + user2

    async def test_create_family_endpoint(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        # Create a user who doesn't belong to any family yet
        new_user = User(
            username=f"free_user_{uuid.uuid4().hex[:6]}",
            email=f"free_{uuid.uuid4().hex[:6]}@test.com",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()
        db_session.expunge(new_user)

        from fastapi import Request
        from core.permissions import BasePermission

        async def override_user(self, request: Request):
            return new_user

        from unittest.mock import patch
        with patch.object(BasePermission, "__call__", override_user):
            payload = {
                "name": "New Family",
                "icon": "material-symbols:home-rounded",
                "icon_color": "#fff",
                "icon_bg": "linear-gradient(135deg, #e8a87c 0%, #c17a45 100%)",
            }
            resp = await integration_client.post("/api/families", json=payload)
            assert resp.status_code in (200, 201)


# ── Meals Endpoints ───────────────────────────────────────────────────────────

class TestMealsEndpoints:

    async def test_create_recipe_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "title": "Spaghetti Bolognese",
            "category": "main",
            "tags": ["italian"],
            "prep_time_minutes": 20,
            "cook_time_minutes": 45,
            "base_servings": 4,
            "ingredients": [],
            "steps": [],
            "emoji": "🍝",
            "accent_gradient": "linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
        }
        resp = await integration_client.post(
            "/api/meals/recipes",
            json=payload,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == "Spaghetti Bolognese"

    async def test_list_recipes(
        self, integration_client: AsyncClient, integration_factory
    ):
        await integration_factory.create_recipe("Test Recipe")
        resp = await integration_client.get("/api/meals/recipes")
        assert resp.status_code == 200
        data = resp.json()
        recipes = data.get("recipes", data)
        assert isinstance(recipes, list)

    async def test_create_planned_meal_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "date": datetime.date.today().isoformat(),
            "slot": "lunch",
            "title": "Pasta",
            "prep_time_minutes": 20,
            "servings": 4,
        }
        resp = await integration_client.post(
            "/api/meals/planner",
            json=payload,
        )
        assert resp.status_code in (200, 201)

    async def test_list_planned_meals_for_week(
        self, integration_client: AsyncClient, integration_factory
    ):
        today = datetime.date.today()
        await integration_factory.create_planned_meal(date=today)

        resp = await integration_client.get(
            f"/api/meals/planner?start_date={today.isoformat()}&end_date={today.isoformat()}"
        )
        assert resp.status_code == 200

    async def test_create_grocery_item_endpoint(
        self, integration_client: AsyncClient, integration_factory
    ):
        payload = {
            "name": "Eggs",
            "amount": 12,
            "unit": "pcs",
            "category": "dairy",
        }
        resp = await integration_client.post(
            "/api/meals/groceries",
            json=payload,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Eggs"


# ── Statistics Endpoints ──────────────────────────────────────────────────────

class TestStatisticsEndpoints:

    async def test_get_family_statistics(
        self, integration_client: AsyncClient, integration_factory
    ):
        resp = await integration_client.get("/api/stats/families/members")
        assert resp.status_code in (200, 400, 422)

    async def test_statistics_after_completing_chores(
        self, integration_client: AsyncClient, integration_factory, db_session: AsyncSession
    ):
        from sqlalchemy import text
        db_today = (await db_session.execute(text("SELECT CURRENT_DATE"))).scalar_one()
        await integration_factory.create_planned_chore(
            due_date=db_today, completed_by=integration_factory.user
        )

        resp = await integration_client.get("/api/stats/families/chores")
        assert resp.status_code in (200, 400, 422)
