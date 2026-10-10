"""
Integration tests for all SQLAlchemy repository classes.

Uses a real PostgreSQL database via testcontainers (configured in conftest.py).
Each test runs inside a transaction that is rolled back after the test, so
tests are fully isolated from each other.

Fixture summary (from conftest.py):
  - db_session        : AsyncSession bound to an open (not-yet-committed) transaction
  - integration_factory : IntegrationFactory with .session/.family/.user/.user2/.chore
                          and async helpers create_planned_chore(), create_quick_chore(),
                          create_schedule(), create_recipe(), create_planned_meal(),
                          create_grocery_item()
"""

import datetime
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores.repository import ChoreRepository
from chores.schemas import ChoreResponseSchema
from core.base_dals import BaseDals, DeleteDALMixin
from core.enums import FrequencyTypeENUM
from core.exceptions.chores import ChoreNotFoundError
from core.exceptions.chores_completion import ChoreCompletionNotFoundError
from core.exceptions.meals import RecipeNotFoundError
from core.exceptions.users import UserNotFoundError
from core.hashing import Hasher
from families.models import Event, Family
from families.repository import EventRepository, FamilyRepository
from families.schemas import EventResponseSchema
from meals.models import GroceryItem, PlannedMeal, Recipe
from meals.repository import GroceryItemRepository, PlannedMealRepository, RecipeRepository
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from planned_chores.repository import (
    ChoreScheduleRepository,
    PlannedChoreRepository,
    QuickPlannedChoreRepository,
)
from users.models import User
from users.repository import UserRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_username(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------------------------------------------------------
# TestUserRepository
# ---------------------------------------------------------------------------


class TestUserRepository:
    """Tests for users.repository.UserRepository"""

    async def test_create_user_with_password_and_get_by_id(
        self, db_session: AsyncSession
    ):
        """create_user_with_password persists the user; get_by_id returns it."""
        repo = UserRepository(db_session)
        username = _unique_username("alice")
        email = _unique_email("alice")

        user = await repo.create_user_with_password(
            username=username,
            hashed_password=Hasher.get_password_hash("S3cret!"),
            name="Alice",
            email=email,
        )

        assert user.id is not None
        fetched = await repo.get_by_id(user.id)
        assert fetched.username == username
        assert fetched.email == email
        assert fetched.name == "Alice"
        assert fetched.is_active is True

    async def test_get_by_id_raises_when_not_found(self, db_session: AsyncSession):
        """get_by_id raises UserNotFoundError for an unknown UUID."""
        repo = UserRepository(db_session)
        with pytest.raises(UserNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_get_by_username_returns_user(self, db_session: AsyncSession):
        """get_by_username returns the correct user by username."""
        repo = UserRepository(db_session)
        username = _unique_username("bob")
        user = await repo.create_user_with_password(
            username=username,
            hashed_password=Hasher.get_password_hash("P@ssw0rd"),
            name="Bob",
            email=_unique_email("bob"),
        )

        result = await repo.get_by_username(username)
        assert result is not None
        assert result.id == user.id

    async def test_get_by_username_returns_none_when_missing(
        self, db_session: AsyncSession
    ):
        """get_by_username returns None for an unknown username."""
        repo = UserRepository(db_session)
        result = await repo.get_by_username("nonexistent_user_xyz")
        assert result is None

    async def test_get_by_username_or_email_by_username(
        self, db_session: AsyncSession
    ):
        """get_by_username_or_email resolves by username."""
        repo = UserRepository(db_session)
        username = _unique_username("carol")
        email = _unique_email("carol")
        user = await repo.create_user_with_password(
            username=username,
            hashed_password=Hasher.get_password_hash("P@ssw0rd"),
            email=email,
        )

        result = await repo.get_by_username_or_email(username)
        assert result is not None
        assert result.id == user.id

    async def test_get_by_username_or_email_by_email(self, db_session: AsyncSession):
        """get_by_username_or_email resolves by email."""
        repo = UserRepository(db_session)
        email = _unique_email("dave")
        user = await repo.create_user_with_password(
            username=_unique_username("dave"),
            hashed_password=Hasher.get_password_hash("P@ssw0rd"),
            email=email,
        )

        result = await repo.get_by_username_or_email(email)
        assert result is not None
        assert result.id == user.id

    async def test_upsert_google_user_creates_new_user(
        self, db_session: AsyncSession
    ):
        """upsert_google_user creates a brand-new user and returns is_new=True."""
        repo = UserRepository(db_session)
        sub = uuid.uuid4().hex
        email = _unique_email("google")

        user, is_new = await repo.upsert_google_user(
            sub=sub, email=email, name="Google User"
        )
        assert is_new is True
        assert user.id is not None
        assert user.google_sub == sub
        assert user.email == email

    async def test_upsert_google_user_returns_existing_user(
        self, db_session: AsyncSession
    ):
        """upsert_google_user returns the existing user and is_new=False."""
        repo = UserRepository(db_session)
        sub = uuid.uuid4().hex
        email = _unique_email("google2")

        user1, _ = await repo.upsert_google_user(sub=sub, email=email)
        user2, is_new = await repo.upsert_google_user(sub=sub, email=email)

        assert is_new is False
        assert user1.id == user2.id

    async def test_increment_experience(self, integration_factory):
        """increment_experience adds the given value to User.experience."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user
        original = user.experience

        await repo.increment_experience(user.id, 50)

        refreshed = await repo.get_by_id(user.id)
        assert refreshed.experience == original + 50

    async def test_decrement_experience_subtracts_value(self, integration_factory):
        """decrement_experience reduces experience when balance is sufficient."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user

        # First give enough experience to subtract from
        await repo.increment_experience(user.id, 100)
        await repo.decrement_experience(user.id, 40)

        refreshed = await repo.get_by_id(user.id)
        assert refreshed.experience == 60

    async def test_decrement_experience_does_not_go_below_zero(
        self, integration_factory
    ):
        """decrement_experience with WHERE experience >= value prevents negatives."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user

        # Ensure experience is 0 (default)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.experience == 0

        # Attempt to subtract more than available — should be a no-op
        await repo.decrement_experience(user.id, 999)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.experience == 0

    async def test_increment_total_completed(self, integration_factory):
        """increment_total_completed increments by 1."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user
        original_tc = (await repo.get_by_id(user.id)).total_completed

        await repo.increment_total_completed(user.id)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.total_completed == original_tc + 1

    async def test_decrement_total_completed(self, integration_factory):
        """decrement_total_completed decrements by 1 when > 0."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user

        await repo.increment_total_completed(user.id)
        await repo.increment_total_completed(user.id)

        before = (await repo.get_by_id(user.id)).total_completed
        await repo.decrement_total_completed(user.id)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.total_completed == before - 1

    async def test_decrement_total_completed_does_not_go_below_zero(
        self, integration_factory
    ):
        """decrement_total_completed is a no-op when total_completed == 0."""
        repo = UserRepository(integration_factory.session)
        user = integration_factory.user

        # Confirm starting value is 0
        current = (await repo.get_by_id(user.id)).total_completed
        assert current == 0

        await repo.decrement_total_completed(user.id)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.total_completed == 0

    async def test_unique_username_constraint(self, db_session: AsyncSession):
        """Inserting two users with the same username raises IntegrityError."""
        username = _unique_username("dup")
        user1 = User(
            username=username,
            email=_unique_email("u1"),
            hashed_password="hash",
            is_active=True,
        )
        user2 = User(
            username=username,  # duplicate!
            email=_unique_email("u2"),
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user1)
        await db_session.flush()
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_unique_email_constraint(self, db_session: AsyncSession):
        """Inserting two users with the same email raises IntegrityError."""
        email = _unique_email("dup")
        user1 = User(
            username=_unique_username("e1"),
            email=email,
            hashed_password="hash",
            is_active=True,
        )
        user2 = User(
            username=_unique_username("e2"),
            email=email,  # duplicate!
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user1)
        await db_session.flush()
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


# ---------------------------------------------------------------------------
# TestFamilyRepository
# ---------------------------------------------------------------------------


class TestFamilyRepository:
    """Tests for families.repository.FamilyRepository"""

    async def test_get_by_id_returns_family(self, integration_factory):
        """get_by_id returns the seeded family by its UUID."""
        repo = FamilyRepository(integration_factory.session)
        family = await repo.get_by_id(integration_factory.family.id)
        assert family.id == integration_factory.family.id
        assert family.name == "Test Family"

    async def test_get_by_id_raises_for_unknown_family(
        self, db_session: AsyncSession
    ):
        """get_by_id raises FamilyNotFoundError for an unknown UUID."""
        from core.exceptions.families import FamilyNotFoundError
        repo = FamilyRepository(db_session)
        with pytest.raises(FamilyNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_user_is_family_admin_returns_true_for_admin(
        self, integration_factory
    ):
        """user_is_family_admin returns True when the user IS the admin."""
        repo = FamilyRepository(integration_factory.session)
        result = await repo.user_is_family_admin(
            user_id=integration_factory.user.id,
            family_id=integration_factory.family.id,
        )
        assert result is True

    async def test_user_is_family_admin_returns_false_for_non_admin(
        self, integration_factory
    ):
        """user_is_family_admin returns False for a non-admin member."""
        repo = FamilyRepository(integration_factory.session)
        result = await repo.user_is_family_admin(
            user_id=integration_factory.user2.id,
            family_id=integration_factory.family.id,
        )
        assert result is False

    async def test_get_family_members_returns_both_users(self, integration_factory):
        """get_family_members returns a list with both seeded users."""
        repo = FamilyRepository(integration_factory.session)
        members = await repo.get_family_members(integration_factory.family.id)
        member_ids = {m.id for m in members}
        assert integration_factory.user.id in member_ids
        assert integration_factory.user2.id in member_ids

    async def test_count_family_members(self, integration_factory):
        """count_family_members returns 2 for the seeded family."""
        repo = FamilyRepository(integration_factory.session)
        count = await repo.count_family_members(integration_factory.family.id)
        assert count == 2

    async def test_family_increment_experience(self, integration_factory):
        """Family.experience increases by the given value."""
        repo = FamilyRepository(integration_factory.session)
        family_id = integration_factory.family.id
        original = (await repo.get_by_id(family_id)).experience

        await repo.increment_experience(family_id, 100)
        refreshed = await repo.get_by_id(family_id)
        assert refreshed.experience == original + 100

    async def test_family_decrement_experience_does_not_go_below_zero(
        self, integration_factory
    ):
        """Family experience cannot go negative via decrement_experience."""
        repo = FamilyRepository(integration_factory.session)
        family_id = integration_factory.family.id

        # Start at 0 (default), attempt to subtract more than available
        current = (await repo.get_by_id(family_id)).experience
        assert current == 0
        await repo.decrement_experience(family_id, 500)
        refreshed = await repo.get_by_id(family_id)
        assert refreshed.experience == 0

    async def test_family_increment_and_decrement_total_completed(
        self, integration_factory
    ):
        """total_completed goes up by increment then down by decrement."""
        repo = FamilyRepository(integration_factory.session)
        family_id = integration_factory.family.id

        await repo.increment_total_completed(family_id)
        await repo.increment_total_completed(family_id)
        after_inc = (await repo.get_by_id(family_id)).total_completed

        await repo.decrement_total_completed(family_id)
        after_dec = (await repo.get_by_id(family_id)).total_completed

        assert after_dec == after_inc - 1

    async def test_family_decrement_total_completed_no_below_zero(
        self, integration_factory
    ):
        """Family total_completed stays at 0 if already 0."""
        repo = FamilyRepository(integration_factory.session)
        family_id = integration_factory.family.id

        current = (await repo.get_by_id(family_id)).total_completed
        assert current == 0
        await repo.decrement_total_completed(family_id)
        assert (await repo.get_by_id(family_id)).total_completed == 0


# ---------------------------------------------------------------------------
# TestEventRepository
# ---------------------------------------------------------------------------


class TestEventRepository:
    """Tests for families.repository.EventRepository"""

    def _make_event(self, family_id: uuid.UUID, dt: datetime.datetime) -> Event:
        return Event(
            name="Birthday Party",
            description="Annual birthday event",
            date=dt,
            family_id=family_id,
            icon="material-symbols:cake",
            icon_color="#ffffff",
            icon_bg="linear-gradient(135deg, #F97316 0%, #FB7185 100%)",
            created_at=datetime.datetime.utcnow(),
        )

    async def test_create_event_and_get_by_id(self, integration_factory):
        """create persists an event; get_by_id retrieves it."""
        repo = EventRepository(integration_factory.session)
        dt = datetime.datetime(2027, 12, 31, 18, 0, 0)
        event = self._make_event(integration_factory.family.id, dt)

        created = await repo.create(event)
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched.name == "Birthday Party"
        assert fetched.family_id == integration_factory.family.id

    async def test_get_by_date_range_returns_matching_events(
        self, integration_factory
    ):
        """get_by_date_range returns events within the given datetime window."""
        repo = EventRepository(integration_factory.session)
        family_id = integration_factory.family.id

        inside_dt = datetime.datetime(2027, 6, 15, 10, 0)
        outside_dt = datetime.datetime(2027, 1, 1, 0, 0)

        await repo.create(self._make_event(family_id, inside_dt))
        await repo.create(self._make_event(family_id, outside_dt))

        date_from = datetime.datetime(2027, 6, 1)
        date_to = datetime.datetime(2027, 7, 1)
        results = await repo.get_by_date_range(family_id, date_from, date_to)

        assert len(results) >= 1
        for r in results:
            assert r.date >= date_from
            assert r.date < date_to

    async def test_get_upcoming_returns_future_events(self, integration_factory):
        """get_upcoming returns events on or after today, limited by `limit`."""
        repo = EventRepository(integration_factory.session)
        family_id = integration_factory.family.id

        future = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        past = datetime.datetime.utcnow() - datetime.timedelta(days=30)

        await repo.create(self._make_event(family_id, future))
        await repo.create(self._make_event(family_id, past))

        upcoming = await repo.get_upcoming(family_id, limit=10)
        today = datetime.datetime.utcnow().date()
        for item in upcoming:
            assert item.date.date() >= today

    async def test_get_all_paginated(self, integration_factory):
        """get_all_paginated respects limit and offset."""
        repo = EventRepository(integration_factory.session)
        family_id = integration_factory.family.id

        for i in range(5):
            dt = datetime.datetime(2026, 9, i + 1, 12, 0)
            await repo.create(self._make_event(family_id, dt))

        page1 = await repo.get_all_paginated(family_id, limit=3, offset=0)
        page2 = await repo.get_all_paginated(family_id, limit=3, offset=3)

        assert len(page1) == 3
        # page2 should have at least 2 events (we created 5)
        assert len(page2) >= 2
        # No overlapping IDs between pages
        page1_ids = {e.id for e in page1}
        page2_ids = {e.id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)


# ---------------------------------------------------------------------------
# TestChoreRepository
# ---------------------------------------------------------------------------


class TestChoreRepository:
    """Tests for chores.repository.ChoreRepository"""

    async def test_create_chore_and_get_by_id(self, integration_factory):
        """create persists a chore; get_by_id retrieves it."""
        repo = ChoreRepository(integration_factory.session)
        chore = Chore(
            name="Vacuum Living Room",
            description="Vacuum the entire living room",
            valuation=15,
            family_id=integration_factory.family.id,
            icon="material-symbols:vacuum-cleaner",
            icon_color="#ffffff",
            icon_bg="#2196F3",
            created_by=integration_factory.user.id,
            is_active=True,
        )

        created = await repo.create(chore)
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched.name == "Vacuum Living Room"
        assert fetched.valuation == 15

    async def test_get_by_id_raises_for_unknown_chore(self, db_session: AsyncSession):
        """get_by_id raises ChoreNotFoundError for an unknown UUID."""
        repo = ChoreRepository(db_session)
        with pytest.raises(ChoreNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_get_all_family_chores_returns_chore_response_schemas(
        self, integration_factory
    ):
        """get_family_chores returns a list of ChoreResponseSchema items."""
        repo = ChoreRepository(integration_factory.session)
        results = await repo.get_family_chores(integration_factory.family.id)

        assert isinstance(results, list)
        assert len(results) >= 1
        for item in results:
            assert isinstance(item, ChoreResponseSchema)

    async def test_get_family_chores_only_returns_active(
        self, integration_factory
    ):
        """get_family_chores excludes soft-deleted (is_active=False) chores."""
        repo = ChoreRepository(integration_factory.session)
        family_id = integration_factory.family.id

        inactive_chore = Chore(
            name="Inactive Chore",
            valuation=5,
            family_id=family_id,
            icon="material-symbols:close",
            icon_color="#ffffff",
            icon_bg="#000000",
            created_by=integration_factory.user.id,
            is_active=False,
        )
        integration_factory.session.add(inactive_chore)
        await integration_factory.session.flush()

        results = await repo.get_family_chores(family_id)
        result_ids = {c.id for c in results}
        assert inactive_chore.id not in result_ids

    async def test_get_family_chores_with_limit(self, integration_factory):
        """get_family_chores respects the limit parameter."""
        repo = ChoreRepository(integration_factory.session)
        family_id = integration_factory.family.id

        # Add extra chores so we have at least 3
        for i in range(3):
            ch = Chore(
                name=f"Extra Chore {i}",
                valuation=5,
                family_id=family_id,
                icon="material-symbols:mop",
                icon_color="#fff",
                icon_bg="#333",
                created_by=integration_factory.user.id,
                is_active=True,
            )
            integration_factory.session.add(ch)
        await integration_factory.session.flush()

        results = await repo.get_family_chores(family_id, limit=2)
        assert len(results) == 2

    async def test_foreign_key_constraint_on_chore_family_id(
        self, db_session: AsyncSession
    ):
        """Inserting a chore with a non-existent family_id raises IntegrityError."""
        bad_chore = Chore(
            name="Orphan Chore",
            valuation=10,
            family_id=uuid.uuid4(),  # does not exist
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#333",
            is_active=True,
        )
        db_session.add(bad_chore)
        with pytest.raises(IntegrityError):
            await db_session.flush()


# ---------------------------------------------------------------------------
# TestPlannedChoreRepository
# ---------------------------------------------------------------------------


class TestPlannedChoreRepository:
    """Tests for planned_chores.repository.PlannedChoreRepository"""

    async def test_create_planned_chore_and_get_by_id(self, integration_factory):
        """create persists a PlannedChore; get_by_id retrieves it."""
        repo = PlannedChoreRepository(integration_factory.session)
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today()
        )

        fetched = await repo.get_by_id(pc.id)
        assert fetched.id == pc.id
        assert fetched.chore_id == integration_factory.chore.id

    async def test_get_by_id_raises_when_not_found(self, db_session: AsyncSession):
        """get_by_id raises ChoreCompletionNotFoundError for an unknown UUID."""
        repo = PlannedChoreRepository(db_session)
        with pytest.raises(ChoreCompletionNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_get_planned_chore_by_id_returns_response_schema(
        self, integration_factory
    ):
        """get_planned_chore_by_id returns a PlannedChoreResponseSchema with joins."""
        repo = PlannedChoreRepository(integration_factory.session)
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today()
        )

        schema = await repo.get_planned_chore_by_id(pc.id)
        assert schema is not None
        assert schema.id == pc.id
        assert schema.chore is not None
        assert schema.chore.name == integration_factory.chore.name

    async def test_get_planned_chore_by_id_returns_none_for_inactive(
        self, integration_factory
    ):
        """get_planned_chore_by_id returns None for an inactive planned chore."""
        repo = PlannedChoreRepository(integration_factory.session)
        pc = await integration_factory.create_planned_chore()

        # Soft-delete it first
        await repo.soft_delete(pc.id)

        schema = await repo.get_planned_chore_by_id(pc.id)
        assert schema is None

    async def test_soft_delete_sets_is_active_false(self, integration_factory):
        """soft_delete marks the PlannedChore as inactive."""
        repo = PlannedChoreRepository(integration_factory.session)
        pc = await integration_factory.create_planned_chore()
        assert pc.is_active is True

        deleted = await repo.soft_delete(pc.id)
        assert deleted is True

        result = await integration_factory.session.execute(
            select(PlannedChore).where(PlannedChore.id == pc.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False

    async def test_hard_delete_removes_row(self, integration_factory):
        """hard_delete physically removes the row from the database."""
        repo = PlannedChoreRepository(integration_factory.session)
        pc = await integration_factory.create_planned_chore()
        pc_id = pc.id

        await repo.hard_delete(pc_id)

        result = await integration_factory.session.execute(
            select(PlannedChore).where(PlannedChore.id == pc_id)
        )
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# TestChoreScheduleRepository
# ---------------------------------------------------------------------------


class TestChoreScheduleRepository:
    """Tests for planned_chores.repository.ChoreScheduleRepository"""

    async def test_create_schedule_and_get_by_id(self, integration_factory):
        """create persists a ChoreSchedule; get_by_id retrieves it."""
        repo = ChoreScheduleRepository(integration_factory.session)
        schedule = await integration_factory.create_schedule(
            frequency=FrequencyTypeENUM.weekly, interval=2
        )

        fetched = await repo.get_by_id(schedule.id)
        assert fetched is not None
        assert fetched.id == schedule.id
        assert fetched.frequency_type == FrequencyTypeENUM.weekly
        assert fetched.interval == 2

    async def test_get_by_id_returns_none_for_unknown_schedule(
        self, db_session: AsyncSession
    ):
        """get_by_id returns None (not an exception) for an unknown UUID."""
        repo = ChoreScheduleRepository(db_session)
        result = await repo.get_by_id(uuid.uuid4())
        assert result is None

    async def test_soft_delete_schedule(self, integration_factory):
        """soft_delete sets is_active=False on the ChoreSchedule."""
        repo = ChoreScheduleRepository(integration_factory.session)
        schedule = await integration_factory.create_schedule()
        assert schedule.is_active is True

        success = await repo.soft_delete(schedule.id)
        assert success is True

        result = await integration_factory.session.execute(
            select(ChoreSchedule).where(ChoreSchedule.id == schedule.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False

    async def test_get_active_schedules_for_family(self, integration_factory):
        """get_active_schedules_for_family returns only active schedules."""
        repo = ChoreScheduleRepository(integration_factory.session)
        family_id = integration_factory.family.id

        active = await integration_factory.create_schedule()
        inactive = await integration_factory.create_schedule()
        await repo.soft_delete(inactive.id)

        results = await repo.get_active_schedules_for_family(family_id)
        result_ids = {s.id for s in results}
        assert active.id in result_ids
        assert inactive.id not in result_ids


# ---------------------------------------------------------------------------
# TestQuickPlannedChoreRepository
# ---------------------------------------------------------------------------


class TestQuickPlannedChoreRepository:
    """Tests for planned_chores.repository.QuickPlannedChoreRepository"""

    async def test_create_quick_chore_and_get_by_id(self, integration_factory):
        """create persists a QuickPlannedChore; get_by_id retrieves it."""
        repo = QuickPlannedChoreRepository(integration_factory.session)
        qc = await integration_factory.create_quick_chore(
            due_date=datetime.date.today()
        )

        fetched = await repo.get_by_id(qc.id)
        assert fetched.id == qc.id
        assert fetched.name == "Quick Task"
        assert fetched.valuation == 5

    async def test_get_by_id_raises_when_not_found(self, db_session: AsyncSession):
        """get_by_id raises ChoreCompletionNotFoundError for an unknown UUID."""
        repo = QuickPlannedChoreRepository(db_session)
        with pytest.raises(ChoreCompletionNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_soft_delete_quick_chore(self, integration_factory):
        """soft_delete marks the QuickPlannedChore as inactive."""
        repo = QuickPlannedChoreRepository(integration_factory.session)
        qc = await integration_factory.create_quick_chore()

        success = await repo.soft_delete(qc.id)
        assert success is True

        result = await integration_factory.session.execute(
            select(QuickPlannedChore).where(QuickPlannedChore.id == qc.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False


# ---------------------------------------------------------------------------
# TestRecipeRepository
# ---------------------------------------------------------------------------


class TestRecipeRepository:
    """Tests for meals.repository.RecipeRepository"""

    async def test_create_recipe_and_get_by_id(self, integration_factory):
        """create persists a Recipe; get_by_id retrieves it."""
        repo = RecipeRepository(integration_factory.session)
        recipe = await integration_factory.create_recipe("Spaghetti Bolognese")

        fetched = await repo.get_by_id(recipe.id)
        assert fetched.id == recipe.id
        assert fetched.title == "Spaghetti Bolognese"
        assert fetched.is_active is True

    async def test_get_by_id_raises_for_unknown_recipe(self, db_session: AsyncSession):
        """get_by_id raises RecipeNotFoundError for an unknown UUID."""
        repo = RecipeRepository(db_session)
        with pytest.raises(RecipeNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_get_family_recipes_returns_active_recipes(
        self, integration_factory
    ):
        """get_family_recipes returns active recipes for the family."""
        repo = RecipeRepository(integration_factory.session)
        family_id = integration_factory.family.id

        await integration_factory.create_recipe("Recipe A")
        await integration_factory.create_recipe("Recipe B")

        results = await repo.get_family_recipes(family_id)
        assert isinstance(results, list)
        assert len(results) >= 2

    async def test_get_family_recipes_excludes_inactive(self, integration_factory):
        """get_family_recipes does not return soft-deleted recipes."""
        repo = RecipeRepository(integration_factory.session)
        family_id = integration_factory.family.id

        recipe = await integration_factory.create_recipe("Will Be Deleted")
        await repo.soft_delete(recipe.id)

        results = await repo.get_family_recipes(family_id)
        result_ids = {r.id for r in results}
        assert recipe.id not in result_ids

    async def test_get_family_recipes_filter_by_category(self, integration_factory):
        """get_family_recipes filters by category when specified."""
        repo = RecipeRepository(integration_factory.session)
        family_id = integration_factory.family.id

        # Default category is "quick"; create one with a different category
        special = Recipe(
            family_id=family_id,
            created_by_id=integration_factory.user.id,
            title="Gourmet Dinner",
            category="gourmet",
            tags=[],
            ingredients=[],
            steps=[],
            is_active=True,
        )
        integration_factory.session.add(special)
        await integration_factory.session.flush()
        await integration_factory.session.refresh(special)

        results = await repo.get_family_recipes(family_id, category="gourmet")
        result_ids = {r.id for r in results}
        assert special.id in result_ids
        # Recipes with category="quick" should not appear
        for r in results:
            assert r.category == "gourmet"

    async def test_toggle_favorite_flips_flag(self, integration_factory):
        """toggle_favorite switches is_favorite from False → True → False."""
        repo = RecipeRepository(integration_factory.session)
        recipe = await integration_factory.create_recipe("Salad")

        assert recipe.is_favorite is False

        toggled = await repo.toggle_favorite(recipe)
        assert toggled.is_favorite is True

        toggled_back = await repo.toggle_favorite(toggled)
        assert toggled_back.is_favorite is False

    async def test_soft_delete_recipe(self, integration_factory):
        """soft_delete sets is_active=False on the Recipe."""
        repo = RecipeRepository(integration_factory.session)
        recipe = await integration_factory.create_recipe("Delete Me")
        assert recipe.is_active is True

        success = await repo.soft_delete(recipe.id)
        assert success is True

        result = await integration_factory.session.execute(
            select(Recipe).where(Recipe.id == recipe.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False


# ---------------------------------------------------------------------------
# TestPlannedMealRepository
# ---------------------------------------------------------------------------


class TestPlannedMealRepository:
    """Tests for meals.repository.PlannedMealRepository"""

    async def test_create_planned_meal_and_get_by_id(self, integration_factory):
        """create persists a PlannedMeal; get_by_id retrieves it."""
        repo = PlannedMealRepository(integration_factory.session)
        meal = await integration_factory.create_planned_meal(
            date=datetime.date.today(), slot="dinner"
        )

        fetched = await repo.get_by_id(meal.id)
        assert fetched.id == meal.id
        assert fetched.slot == "dinner"

    async def test_get_family_meals_date_range(self, integration_factory):
        """get_family_meals returns only meals within the given date range."""
        repo = PlannedMealRepository(integration_factory.session)
        family_id = integration_factory.family.id

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        next_week = today + datetime.timedelta(days=7)
        far_future = today + datetime.timedelta(days=30)

        await integration_factory.create_planned_meal(date=yesterday, slot="breakfast")
        await integration_factory.create_planned_meal(date=today, slot="lunch")
        await integration_factory.create_planned_meal(date=far_future, slot="dinner")

        results = await repo.get_family_meals(
            family_id=family_id,
            start_date=yesterday,
            end_date=next_week,
        )
        result_dates = {m.date for m in results}

        assert yesterday in result_dates
        assert today in result_dates
        assert far_future not in result_dates

    async def test_get_family_meals_excludes_inactive(self, integration_factory):
        """get_family_meals does not return soft-deleted meals."""
        repo = PlannedMealRepository(integration_factory.session)
        meal = await integration_factory.create_planned_meal()

        await repo.soft_delete(meal.id)

        results = await repo.get_family_meals(
            family_id=integration_factory.family.id,
            start_date=datetime.date.today() - datetime.timedelta(days=1),
            end_date=datetime.date.today() + datetime.timedelta(days=1),
        )
        result_ids = {m.id for m in results}
        assert meal.id not in result_ids

    async def test_soft_delete_planned_meal(self, integration_factory):
        """soft_delete sets is_active=False on the PlannedMeal."""
        repo = PlannedMealRepository(integration_factory.session)
        meal = await integration_factory.create_planned_meal()

        success = await repo.soft_delete(meal.id)
        assert success is True

        result = await integration_factory.session.execute(
            select(PlannedMeal).where(PlannedMeal.id == meal.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False

    async def test_create_planned_meal_with_recipe(self, integration_factory):
        """A PlannedMeal can be linked to a Recipe via recipe_id."""
        repo = PlannedMealRepository(integration_factory.session)
        recipe = await integration_factory.create_recipe("Risotto")
        meal = await integration_factory.create_planned_meal(
            date=datetime.date.today(), slot="lunch", recipe=recipe
        )

        fetched = await repo.get_by_id(meal.id)
        assert fetched.recipe_id == recipe.id


# ---------------------------------------------------------------------------
# TestGroceryItemRepository
# ---------------------------------------------------------------------------


class TestGroceryItemRepository:
    """Tests for meals.repository.GroceryItemRepository"""

    async def test_create_grocery_item_and_get_by_id(self, integration_factory):
        """create persists a GroceryItem; get_by_id retrieves it."""
        repo = GroceryItemRepository(integration_factory.session)
        item = await integration_factory.create_grocery_item("Eggs")

        fetched = await repo.get_by_id(item.id)
        assert fetched.id == item.id
        assert fetched.name == "Eggs"
        assert fetched.is_bought is False

    async def test_toggle_bought_false_to_true(self, integration_factory):
        """Toggling is_bought from False to True via update."""
        repo = GroceryItemRepository(integration_factory.session)
        item = await integration_factory.create_grocery_item("Bread")

        assert item.is_bought is False
        item.is_bought = True
        updated = await repo.update(item)
        assert updated.is_bought is True

    async def test_toggle_bought_true_to_false(self, integration_factory):
        """Toggling is_bought from True back to False via update."""
        repo = GroceryItemRepository(integration_factory.session)
        item = await integration_factory.create_grocery_item("Cheese")

        item.is_bought = True
        await repo.update(item)

        item.is_bought = False
        updated = await repo.update(item)
        assert updated.is_bought is False

    async def test_get_family_items_returns_active_items(self, integration_factory):
        """get_family_items returns active grocery items ordered correctly."""
        repo = GroceryItemRepository(integration_factory.session)
        family_id = integration_factory.family.id

        milk = await integration_factory.create_grocery_item("Milk")
        butter = await integration_factory.create_grocery_item("Butter")

        results = await repo.get_family_items(family_id)
        result_ids = {i.id for i in results}
        assert milk.id in result_ids
        assert butter.id in result_ids

    async def test_get_family_items_excludes_inactive(self, integration_factory):
        """get_family_items excludes soft-deleted items."""
        repo = GroceryItemRepository(integration_factory.session)
        item = await integration_factory.create_grocery_item("Yogurt")
        await repo.soft_delete(item.id)

        results = await repo.get_family_items(integration_factory.family.id)
        result_ids = {i.id for i in results}
        assert item.id not in result_ids

    async def test_soft_delete_grocery_item(self, integration_factory):
        """soft_delete sets is_active=False on the GroceryItem."""
        repo = GroceryItemRepository(integration_factory.session)
        item = await integration_factory.create_grocery_item("Orange")

        success = await repo.soft_delete(item.id)
        assert success is True

        result = await integration_factory.session.execute(
            select(GroceryItem).where(GroceryItem.id == item.id)
        )
        refreshed = result.scalar_one()
        assert refreshed.is_active is False


# ---------------------------------------------------------------------------
# TestBaseDals
# ---------------------------------------------------------------------------


class TestBaseDals:
    """Tests for core.base_dals.BaseDals generic behaviour."""

    async def test_get_by_id_raises_not_found_error_on_missing_uuid(
        self, db_session: AsyncSession
    ):
        """Any repository that inherits BaseDals raises its not_found_exception."""
        # UserRepository is a concrete BaseDals implementation
        repo = UserRepository(db_session)
        with pytest.raises(UserNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_chore_repo_raises_chore_not_found(self, db_session: AsyncSession):
        """ChoreRepository raises ChoreNotFoundError (not UserNotFoundError)."""
        repo = ChoreRepository(db_session)
        with pytest.raises(ChoreNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_recipe_repo_raises_recipe_not_found(self, db_session: AsyncSession):
        """RecipeRepository raises RecipeNotFoundError."""
        repo = RecipeRepository(db_session)
        with pytest.raises(RecipeNotFoundError):
            await repo.get_by_id(uuid.uuid4())

    async def test_create_returns_object_with_id(self, integration_factory):
        """BaseDals.create assigns a primary key and returns the flushed object."""
        repo = ChoreRepository(integration_factory.session)
        chore = Chore(
            name="Mop Floor",
            valuation=8,
            family_id=integration_factory.family.id,
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#333",
            is_active=True,
        )
        created = await repo.create(chore)
        assert created.id is not None
        assert isinstance(created.id, uuid.UUID)


# ---------------------------------------------------------------------------
# TestDeleteDALMixin
# ---------------------------------------------------------------------------


class TestDeleteDALMixin:
    """Tests for core.base_dals.DeleteDALMixin soft_delete / hard_delete."""

    async def test_soft_delete_sets_is_active_false(self, integration_factory):
        """DeleteDALMixin.soft_delete sets is_active=False and returns True."""
        repo = ChoreRepository(integration_factory.session)  # uses DeleteDALMixin
        chore = Chore(
            name="Sweep Porch",
            valuation=5,
            family_id=integration_factory.family.id,
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#444",
            is_active=True,
        )
        created = await repo.create(chore)
        assert created.is_active is True

        result = await repo.soft_delete(created.id)
        assert result is True

        row = await integration_factory.session.execute(
            select(Chore).where(Chore.id == created.id)
        )
        refreshed = row.scalar_one()
        assert refreshed.is_active is False

    async def test_soft_delete_returns_false_for_nonexistent_id(
        self, db_session: AsyncSession
    ):
        """DeleteDALMixin.soft_delete returns False when no rows are matched."""
        repo = ChoreRepository(db_session)
        result = await repo.soft_delete(uuid.uuid4())
        assert result is False

    async def test_hard_delete_removes_row(self, integration_factory):
        """DeleteDALMixin.hard_delete physically removes the row."""
        repo = ChoreRepository(integration_factory.session)
        chore = Chore(
            name="Throw Away",
            valuation=1,
            family_id=integration_factory.family.id,
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#555",
            is_active=True,
        )
        created = await repo.create(chore)
        chore_id = created.id

        await repo.hard_delete(chore_id)

        row = await integration_factory.session.execute(
            select(Chore).where(Chore.id == chore_id)
        )
        assert row.scalar_one_or_none() is None

    async def test_hard_delete_is_idempotent_for_nonexistent_id(
        self, db_session: AsyncSession
    ):
        """hard_delete on a missing UUID does not raise an exception."""
        repo = ChoreRepository(db_session)
        # Should silently succeed without raising
        await repo.hard_delete(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestConstraints — Database-level integrity guarantees
# ---------------------------------------------------------------------------


class TestConstraints:
    """Verify critical database constraints are enforced end-to-end."""

    async def test_fk_cascade_delete_family_removes_planned_chores(
        self, db_session: AsyncSession
    ):
        """
        Deleting a Family cascades to PlannedChore rows (ondelete=CASCADE).

        We create a temporary family + user + chore + planned_chore, then
        hard-delete the family row and confirm the planned chore is gone.
        """
        # -- Set up a standalone family / user / chore in the session --
        user = User(
            username=_unique_username("casc"),
            email=_unique_email("casc"),
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        family = Family(
            name="Temp Family",
            family_admin_id=user.id,
        )
        db_session.add(family)
        await db_session.flush()

        user.family_id = family.id
        db_session.add(user)
        await db_session.flush()

        chore = Chore(
            name="Cascade Test Chore",
            valuation=1,
            family_id=family.id,
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#999",
            is_active=True,
        )
        db_session.add(chore)
        await db_session.flush()

        pc = PlannedChore(
            chore_id=chore.id,
            family_id=family.id,
            due_date=datetime.date.today(),
            assigned_to_id=user.id,
            created_by=user.id,
            is_active=True,
        )
        db_session.add(pc)
        await db_session.flush()
        pc_id = pc.id

        # Delete the family using raw DELETE so cascade fires
        await db_session.execute(
            text("DELETE FROM family WHERE id = :fid").bindparams(fid=family.id)
        )
        await db_session.flush()

        # PlannedChore should be gone due to CASCADE
        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.id == pc_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_chore_fk_requires_valid_family(self, db_session: AsyncSession):
        """A Chore with a non-existent family_id violates the FK constraint."""
        orphan = Chore(
            name="No Family Chore",
            valuation=5,
            family_id=uuid.uuid4(),  # non-existent
            icon="material-symbols:mop",
            icon_color="#fff",
            icon_bg="#333",
            is_active=True,
        )
        db_session.add(orphan)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_duplicate_username_raises_integrity_error(
        self, db_session: AsyncSession
    ):
        """Two users with the same username → IntegrityError (unique constraint)."""
        uname = _unique_username("same")
        db_session.add(
            User(username=uname, email=_unique_email("s1"), hashed_password="x", is_active=True)
        )
        await db_session.flush()

        db_session.add(
            User(username=uname, email=_unique_email("s2"), hashed_password="x", is_active=True)
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_duplicate_email_raises_integrity_error(
        self, db_session: AsyncSession
    ):
        """Two users with the same email → IntegrityError (unique constraint)."""
        email = _unique_email("dup")
        db_session.add(
            User(username=_unique_username("d1"), email=email, hashed_password="x", is_active=True)
        )
        await db_session.flush()

        db_session.add(
            User(username=_unique_username("d2"), email=email, hashed_password="x", is_active=True)
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()
