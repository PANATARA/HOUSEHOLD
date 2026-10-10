"""
Integration tests for all service classes.

Uses a real PostgreSQL container (via testcontainers) with Alembic migrations applied.
Every test runs inside a transaction that is rolled back on teardown, providing full isolation.

Services under test:
    - UserCreatorService
    - FamilyCreatorService / AddUserToFamilyService
    - ChoreCreatorService / UpdateChoreService
    - CreatePlannedChore / DeletePlannedChore / CompletePlannedChore / UncompletePlannedChore
    - CreateChoreSchedule
    - CreateQuickPlannedChore / CompleteQuickPlannedChore / UncompleteQuickPlannedChore
    - DeleteQuickPlannedChore
    - RecipeCreatorService / RecipeUpdateService
"""

import datetime
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from chores.services import ChoreCreatorService, UpdateChoreService
from chores.schemas import ChoreCreateSchema, ChoreUpdateSchema
from core.enums import FrequencyTypeENUM
from core.exceptions.chores_completion import ChoreCompletionCanNotBeChanged
from core.exceptions.users import UserAlreadyExistsError
from families.models import Family
from families.services import AddUserToFamilyService, FamilyCreatorService
from meals.schemas import RecipeCreateSchema, RecipeUpdateSchema
from meals.services import RecipeCreatorService, RecipeUpdateService
from planned_chores.models import ChoreSchedule, PlannedChore
from planned_chores.services import (
    CompleteQuickPlannedChore,
    CompletePlannedChore,
    CreateChoreSchedule,
    CreatePlannedChore,
    CreateQuickPlannedChore,
    DeletePlannedChore,
    DeleteQuickPlannedChore,
    UncompleteQuickPlannedChore,
    UncompletePlannedChore,
)
from users.models import User, UserSettings
from users.schemas import UserFamilyPermissionModelSchema
from users.services import UserCreatorService


# ─── Helper factories ──────────────────────────────────────────────────────────


def _unique(prefix: str = "user") -> str:
    """Return a short unique slug suitable for usernames / names."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ══════════════════════════════════════════════════════════════════════════════
# 1. UserCreatorService
# ══════════════════════════════════════════════════════════════════════════════


class TestUserCreatorService:
    """Integration tests for UserCreatorService."""

    async def test_creates_user_with_hashed_password(self, db_session):
        """Service should persist a new User row with a non-plaintext password."""
        username = _unique("alice")
        svc = UserCreatorService(
            username=username,
            password="Str0ng!Pass",
            email=f"{username}@example.com",
            name="Alice",
            db_session=db_session,
        )
        user = await svc.run_process()

        # Re-fetch from DB to confirm persistence
        result = await db_session.execute(select(User).where(User.username == username))
        db_user = result.scalar_one()

        assert db_user.id == user.id
        assert db_user.username == username
        assert db_user.hashed_password is not None
        assert db_user.hashed_password != "Str0ng!Pass"  # must be hashed

    async def test_creates_associated_settings(self, db_session):
        """Service must also create a UserSettings record for the new user."""
        username = _unique("bob")
        svc = UserCreatorService(
            username=username,
            password="Str0ng!Pass",
            db_session=db_session,
        )
        user = await svc.run_process()

        result = await db_session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()

        assert settings is not None
        assert settings.user_id == user.id

    async def test_raises_on_duplicate_username(self, db_session, integration_factory):
        """Creating a user with an already-taken username must raise UserAlreadyExistsError."""
        existing_username = integration_factory.user.username
        svc = UserCreatorService(
            username=existing_username,
            password="AnotherP@ss1",
            db_session=db_session,
        )
        with pytest.raises(UserAlreadyExistsError):
            await svc.run_process()

    async def test_creates_user_without_password(self, db_session):
        """Service should allow password-less users (e.g., Google OAuth)."""
        username = _unique("google_user")
        svc = UserCreatorService(
            username=username,
            db_session=db_session,
        )
        user = await svc.run_process()

        result = await db_session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one()
        assert db_user.hashed_password is None

    async def test_name_defaults_to_username_when_not_provided(self, db_session):
        """When `name` is omitted the service should fall back to the username."""
        username = _unique("nameless")
        svc = UserCreatorService(username=username, db_session=db_session)
        user = await svc.run_process()
        assert user.name == username


# ══════════════════════════════════════════════════════════════════════════════
# 2. FamilyCreatorService / AddUserToFamilyService
# ══════════════════════════════════════════════════════════════════════════════


class TestFamilyCreatorService:
    """Integration tests for FamilyCreatorService."""

    async def test_creates_family_record(self, db_session, integration_factory):
        """FamilyCreatorService should persist a Family row."""
        # Create a fresh user without a family
        user = User(
            username=_unique("admin"),
            name="FamilyAdmin",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        svc = FamilyCreatorService(
            name="The Smiths",
            icon="material-symbols:home-rounded",
            icon_color="#ffffff",
            icon_bg="#333333",
            user=user,
            db_session=db_session,
        )
        family = await svc.run_process()

        result = await db_session.execute(select(Family).where(Family.id == family.id))
        db_family = result.scalar_one()

        assert db_family.name == "The Smiths"
        assert db_family.family_admin_id == user.id

    async def test_creator_user_family_id_is_updated(self, db_session):
        """After FamilyCreatorService runs, the creator's family_id must point to new family."""
        user = User(
            username=_unique("creator"),
            name="Creator",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        svc = FamilyCreatorService(
            name="Creator Family",
            icon="material-symbols:home-rounded",
            icon_color="#ffffff",
            icon_bg="#444444",
            user=user,
            db_session=db_session,
        )
        family = await svc.run_process()
        await db_session.refresh(user)

        assert user.family_id == family.id

    async def test_creator_permissions_are_created(self, db_session):
        """FamilyCreatorService must create UserFamilyPermissions for the admin user."""
        from users.models import UserFamilyPermissions

        user = User(
            username=_unique("perm_admin"),
            name="PermAdmin",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        svc = FamilyCreatorService(
            name="Perm Family",
            icon="material-symbols:home-rounded",
            icon_color="#ffffff",
            icon_bg="#555555",
            user=user,
            db_session=db_session,
        )
        await svc.run_process()

        result = await db_session.execute(
            select(UserFamilyPermissions).where(UserFamilyPermissions.user_id == user.id)
        )
        perms = result.scalar_one_or_none()
        assert perms is not None
        assert perms.can_invite_users is True


class TestAddUserToFamilyService:
    """Integration tests for AddUserToFamilyService."""

    async def test_updates_user_family_id(self, db_session, integration_factory):
        """Service must set user.family_id to the target family's id."""
        # New user without a family
        new_user = User(
            username=_unique("newcomer"),
            name="Newcomer",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.flush()

        svc = AddUserToFamilyService(
            family=integration_factory.family,
            user=new_user,
            permissions=UserFamilyPermissionModelSchema(can_invite_users=False),
            db_session=db_session,
        )
        await svc.run_process()
        await db_session.refresh(new_user)

        assert new_user.family_id == integration_factory.family.id

    async def test_creates_permissions_for_added_user(self, db_session, integration_factory):
        """Service must create a UserFamilyPermissions entry for the new member."""
        from users.models import UserFamilyPermissions

        new_user = User(
            username=_unique("member"),
            name="Member",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.flush()

        svc = AddUserToFamilyService(
            family=integration_factory.family,
            user=new_user,
            permissions=UserFamilyPermissionModelSchema(can_invite_users=True),
            db_session=db_session,
        )
        await svc.run_process()

        result = await db_session.execute(
            select(UserFamilyPermissions).where(UserFamilyPermissions.user_id == new_user.id)
        )
        perms = result.scalar_one_or_none()
        assert perms is not None

    async def test_raises_if_user_already_in_a_family(self, db_session, integration_factory):
        """Validator should reject a user who already belongs to a family."""
        from core.exceptions.families import UserIsAlreadyFamilyMember

        # integration_factory.user already has a family_id
        svc = AddUserToFamilyService(
            family=integration_factory.family,
            user=integration_factory.user,
            permissions=UserFamilyPermissionModelSchema(can_invite_users=False),
            db_session=db_session,
        )
        with pytest.raises(UserIsAlreadyFamilyMember):
            await svc.run_process()


# ══════════════════════════════════════════════════════════════════════════════
# 3. ChoreCreatorService / UpdateChoreService
# ══════════════════════════════════════════════════════════════════════════════


class TestChoreCreatorService:
    """Integration tests for ChoreCreatorService."""

    async def test_creates_chore_in_db(self, db_session, integration_factory):
        """Service must persist a Chore row with the correct family_id."""
        from chores.models import Chore

        data = ChoreCreateSchema(
            name="Vacuum Living Room",
            description="Use the robot vacuum",
            valuation=15,
            icon="material-symbols:vacuum",
            icon_color="#000000",
            icon_bg="#aabbcc",
        )
        svc = ChoreCreatorService(
            family=integration_factory.family,
            data=data,
            db_session=db_session,
        )
        chore = await svc.run_process()

        result = await db_session.execute(
            select(Chore).where(Chore.id == chore.id)
        )
        db_chore = result.scalar_one()

        assert db_chore.name == "Vacuum Living Room"
        assert db_chore.valuation == 15
        assert db_chore.family_id == integration_factory.family.id
        assert db_chore.default_chore_id is None

    async def test_chore_created_with_correct_icon_fields(self, db_session, integration_factory):
        """Service must persist icon metadata exactly as supplied."""
        from chores.models import Chore

        data = ChoreCreateSchema(
            name="Mop Floors",
            icon="material-symbols:mop",
            icon_color="#ff0000",
            icon_bg="linear-gradient(90deg, #fff 0%, #000 100%)",
        )
        svc = ChoreCreatorService(
            family=integration_factory.family,
            data=data,
            db_session=db_session,
        )
        chore = await svc.run_process()

        result = await db_session.execute(select(Chore).where(Chore.id == chore.id))
        db_chore = result.scalar_one()

        assert db_chore.icon == "material-symbols:mop"
        assert db_chore.icon_color == "#ff0000"


class TestUpdateChoreService:
    """Integration tests for UpdateChoreService."""

    async def test_updates_chore_description(self, db_session, integration_factory):
        """Service must persist description changes to the DB."""
        chore = integration_factory.chore
        original_name = chore.name

        data = ChoreUpdateSchema(description="Updated description text")
        svc = UpdateChoreService(chore=chore, data=data, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(chore)
        assert chore.description == "Updated description text"
        # Other fields should remain intact
        assert chore.name == original_name

    async def test_updates_chore_name_and_valuation(self, db_session, integration_factory):
        """Service must update multiple fields in a single call."""
        chore = integration_factory.chore
        data = ChoreUpdateSchema(name="Renamed Chore", valuation=99)
        svc = UpdateChoreService(chore=chore, data=data, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(chore)
        assert chore.name == "Renamed Chore"
        assert chore.valuation == 99

    async def test_raises_when_updating_non_description_field_of_default_chore(
        self, db_session, integration_factory
    ):
        """Validator must block non-description changes on default chores."""
        from chores.models import Chore, DefaultChore

        # Create a fake DefaultChore to satisfy the FK
        default = DefaultChore(
            icon="material-symbols:cleaning",
            icon_color="#fff",
            icon_bg="#000",
            valuation=5,
            order=1,
        )
        db_session.add(default)
        await db_session.flush()

        chore = Chore(
            name="System Wash",
            description="System chore",
            valuation=5,
            family_id=integration_factory.family.id,
            icon="material-symbols:cleaning",
            icon_color="#fff",
            icon_bg="#000",
            default_chore_id=default.id,
            is_active=True,
        )
        db_session.add(chore)
        await db_session.flush()

        # Trying to change `name` (non-description field) must raise
        from core.exceptions.chores import ChoreNotFoundError

        data = ChoreUpdateSchema(name="Hacked Name")
        svc = UpdateChoreService(chore=chore, data=data, db_session=db_session)
        with pytest.raises(ChoreNotFoundError):
            await svc.run_process()

    async def test_allows_updating_description_of_default_chore(
        self, db_session, integration_factory
    ):
        """Description update must be allowed even for default chores."""
        from chores.models import Chore, DefaultChore

        default = DefaultChore(
            icon="material-symbols:clean",
            icon_color="#fff",
            icon_bg="#000",
            valuation=5,
            order=2,
        )
        db_session.add(default)
        await db_session.flush()

        chore = Chore(
            name="System Chore 2",
            description="Original description",
            valuation=5,
            family_id=integration_factory.family.id,
            icon="material-symbols:clean",
            icon_color="#fff",
            icon_bg="#000",
            default_chore_id=default.id,
            is_active=True,
        )
        db_session.add(chore)
        await db_session.flush()

        data = ChoreUpdateSchema(description="Updated description only")
        svc = UpdateChoreService(chore=chore, data=data, db_session=db_session)
        updated = await svc.run_process()

        assert updated.description == "Updated description only"


# ══════════════════════════════════════════════════════════════════════════════
# 4. CreatePlannedChore
# ══════════════════════════════════════════════════════════════════════════════


class TestCreatePlannedChore:
    """Integration tests for CreatePlannedChore."""

    async def test_creates_planned_chore_in_db(self, db_session, integration_factory):
        """Service must persist a PlannedChore linked to the chore and user."""
        due = datetime.date.today()
        svc = CreatePlannedChore(
            schedule=None,
            chore=integration_factory.chore,
            assigned_to_user=integration_factory.user,
            created_by=integration_factory.user,
            due_date=due,
            message="Please do this today",
            db_session=db_session,
        )
        pc = await svc.run_process()

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.id == pc.id)
        )
        db_pc = result.scalar_one()

        assert db_pc.chore_id == integration_factory.chore.id
        assert db_pc.family_id == integration_factory.family.id
        assert db_pc.assigned_to_id == integration_factory.user.id
        assert db_pc.due_date == due
        assert db_pc.completed_by_id is None

    async def test_planned_chore_message_persisted(self, db_session, integration_factory):
        """Message field must be saved as provided."""
        svc = CreatePlannedChore(
            schedule=None,
            chore=integration_factory.chore,
            assigned_to_user=integration_factory.user,
            created_by=integration_factory.user,
            due_date=datetime.date.today(),
            message="Important note",
            db_session=db_session,
        )
        pc = await svc.run_process()
        assert pc.message == "Important note"

    async def test_creates_planned_chore_without_assigned_user(self, db_session, integration_factory):
        """Service must accept None for assigned_to_user."""
        svc = CreatePlannedChore(
            schedule=None,
            chore=integration_factory.chore,
            assigned_to_user=None,
            created_by=integration_factory.user,
            due_date=datetime.date.today(),
            message="",
            db_session=db_session,
        )
        pc = await svc.run_process()
        assert pc.assigned_to_id is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. CompletePlannedChore / UncompletePlannedChore
# ══════════════════════════════════════════════════════════════════════════════


class TestCompletePlannedChore:
    """Integration tests for CompletePlannedChore."""

    async def test_sets_completed_by_id(self, db_session, integration_factory):
        """After completion, planned_chore.completed_by_id must equal the completer's id."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        user = integration_factory.user

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(pc)
        assert pc.completed_by_id == user.id

    async def test_increments_user_experience(self, db_session, integration_factory):
        """Completing a chore must add chore.valuation to user.experience."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        user = integration_factory.user
        chore = integration_factory.chore
        initial_exp = user.experience

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(user)
        assert user.experience == initial_exp + chore.valuation

    async def test_increments_family_experience(self, db_session, integration_factory):
        """Completing a chore must add chore.valuation to family.experience."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        family = integration_factory.family
        chore = integration_factory.chore
        initial_exp = family.experience

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=integration_factory.user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(family)
        assert family.experience == initial_exp + chore.valuation

    async def test_increments_user_total_completed(self, db_session, integration_factory):
        """User.total_completed must increase by 1 on chore completion."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        user = integration_factory.user
        initial_tc = user.total_completed

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(user)
        assert user.total_completed == initial_tc + 1

    async def test_increments_family_total_completed(self, db_session, integration_factory):
        """Family.total_completed must increase by 1 on chore completion."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        family = integration_factory.family
        initial_tc = family.total_completed

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=integration_factory.user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(family)
        assert family.total_completed == initial_tc + 1

    async def test_raises_if_already_completed(self, db_session, integration_factory):
        """Completing an already-completed chore must raise ChoreCompletionCanNotBeChanged."""
        # Pre-complete via factory helper (completed_by set)
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=integration_factory.user,
        )

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=integration_factory.user,
            db_session=db_session,
        )
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await svc.run_process()

    async def test_raises_if_due_date_in_past(self, db_session, integration_factory):
        """Completing a chore with a past due_date must raise ChoreCompletionCanNotBeChanged."""
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        pc = await integration_factory.create_planned_chore(due_date=yesterday)

        svc = CompletePlannedChore(
            planned_chore=pc,
            completed_by=integration_factory.user,
            db_session=db_session,
        )
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await svc.run_process()


class TestUncompletePlannedChore:
    """Integration tests for UncompletePlannedChore."""

    async def test_clears_completed_by_id(self, db_session, integration_factory):
        """After uncomplete, completed_by_id must be None."""
        user = integration_factory.user
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )

        # Seed some experience so decrement doesn't underflow
        user.experience = 100
        await db_session.flush()

        svc = UncompletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(pc)
        assert pc.completed_by_id is None

    async def test_decrements_user_experience(self, db_session, integration_factory):
        """Uncompleting must subtract chore.valuation from user.experience."""
        user = integration_factory.user
        chore = integration_factory.chore
        user.experience = 200
        await db_session.flush()

        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )

        svc = UncompletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(user)
        assert user.experience == 200 - chore.valuation

    async def test_decrements_family_experience(self, db_session, integration_factory):
        """Uncompleting must subtract chore.valuation from family.experience."""
        family = integration_factory.family
        chore = integration_factory.chore
        family.experience = 200
        await db_session.flush()

        user = integration_factory.user
        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )

        svc = UncompletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(family)
        assert family.experience == 200 - chore.valuation

    async def test_raises_if_not_completed(self, db_session, integration_factory):
        """Uncompleting a chore that is not completed must raise ChoreCompletionCanNotBeChanged."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        # pc.completed_by_id is None by default

        svc = UncompletePlannedChore(planned_chore=pc, db_session=db_session)
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await svc.run_process()


# ══════════════════════════════════════════════════════════════════════════════
# 6. DeletePlannedChore
# ══════════════════════════════════════════════════════════════════════════════


class TestDeletePlannedChore:
    """Integration tests for DeletePlannedChore."""

    async def test_hard_deletes_uncompleted_chore(self, db_session, integration_factory):
        """Uncompleted planned chore must be hard-deleted (no row in DB)."""
        pc = await integration_factory.create_planned_chore(due_date=datetime.date.today())
        pc_id = pc.id

        svc = DeletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.id == pc_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_soft_deletes_completed_chore(self, db_session, integration_factory):
        """Completed planned chore must remain in DB but with is_active=False."""
        user = integration_factory.user
        user.experience = 100
        await db_session.flush()

        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )
        pc_id = pc.id

        svc = DeletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.id == pc_id)
        )
        db_pc = result.scalar_one_or_none()
        assert db_pc is not None
        assert db_pc.is_active is False

    async def test_decrements_experience_on_completed_chore_delete(
        self, db_session, integration_factory
    ):
        """Deleting a completed chore must decrement user and family experience."""
        user = integration_factory.user
        family = integration_factory.family
        chore = integration_factory.chore
        user.experience = 100
        family.experience = 100
        await db_session.flush()

        pc = await integration_factory.create_planned_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )

        svc = DeletePlannedChore(planned_chore=pc, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(user)
        await db_session.refresh(family)
        assert user.experience == 100 - chore.valuation
        assert family.experience == 100 - chore.valuation


# ══════════════════════════════════════════════════════════════════════════════
# 7. CreateChoreSchedule
# ══════════════════════════════════════════════════════════════════════════════


class TestCreateChoreSchedule:
    """Integration tests for CreateChoreSchedule."""

    async def test_creates_daily_schedule_in_db(self, db_session, integration_factory):
        """Service must persist a daily ChoreSchedule record."""
        today = datetime.date.today()
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            days_of_week=None,
            day_of_month=None,
            starts_at=today,
            ends_at=None,
            db_session=db_session,
        )
        schedule = await svc.run_process()

        result = await db_session.execute(
            select(ChoreSchedule).where(ChoreSchedule.id == schedule.id)
        )
        db_schedule = result.scalar_one()

        assert db_schedule.frequency_type == FrequencyTypeENUM.daily
        assert db_schedule.chore_id == integration_factory.chore.id
        assert db_schedule.assigned_to_id == integration_factory.user.id

    async def test_creates_weekly_schedule_in_db(self, db_session, integration_factory):
        """Service must persist a weekly ChoreSchedule record with days_of_week bitmask."""
        today = datetime.date.today()
        # Monday + Wednesday bitmask: 0b0000101 = 5
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.weekly,
            interval=1,
            days_of_week=5,
            day_of_month=None,
            starts_at=today,
            ends_at=None,
            db_session=db_session,
        )
        schedule = await svc.run_process()

        result = await db_session.execute(
            select(ChoreSchedule).where(ChoreSchedule.id == schedule.id)
        )
        db_schedule = result.scalar_one()
        assert db_schedule.days_of_week == 5

    async def test_creates_monthly_schedule_in_db(self, db_session, integration_factory):
        """Service must persist a monthly ChoreSchedule record with day_of_month."""
        today = datetime.date.today()
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.monthly,
            interval=1,
            days_of_week=None,
            day_of_month=15,
            starts_at=today,
            ends_at=None,
            db_session=db_session,
        )
        schedule = await svc.run_process()

        result = await db_session.execute(
            select(ChoreSchedule).where(ChoreSchedule.id == schedule.id)
        )
        db_schedule = result.scalar_one()
        assert db_schedule.day_of_month == 15

    async def test_raises_for_weekly_without_days_of_week(self, db_session, integration_factory):
        """Weekly schedule without days_of_week bitmask must raise ValueError."""
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.weekly,
            interval=1,
            days_of_week=None,  # missing!
            day_of_month=None,
            starts_at=datetime.date.today(),
            ends_at=None,
            db_session=db_session,
        )
        with pytest.raises(ValueError, match="days_of_week"):
            await svc.run_process()

    async def test_raises_for_monthly_without_day_of_month(self, db_session, integration_factory):
        """Monthly schedule without day_of_month must raise ValueError."""
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.monthly,
            interval=1,
            days_of_week=None,
            day_of_month=None,  # missing!
            starts_at=datetime.date.today(),
            ends_at=None,
            db_session=db_session,
        )
        with pytest.raises(ValueError, match="day_of_month"):
            await svc.run_process()

    async def test_raises_if_ends_at_before_starts_at(self, db_session, integration_factory):
        """ends_at before starts_at must raise ValueError."""
        today = datetime.date.today()
        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=integration_factory.user,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            days_of_week=None,
            day_of_month=None,
            starts_at=today,
            ends_at=today - datetime.timedelta(days=1),  # ends before starts!
            db_session=db_session,
        )
        with pytest.raises(ValueError, match="ends_at"):
            await svc.run_process()

    async def test_raises_if_assigned_user_not_in_family(self, db_session, integration_factory):
        """Assigning a schedule to a user from a different family must raise ValueError."""
        outsider = User(
            username=_unique("outsider"),
            name="Outsider",
            hashed_password="x",
            is_active=True,
            # No family_id → different family
        )
        db_session.add(outsider)
        await db_session.flush()

        svc = CreateChoreSchedule(
            chore=integration_factory.chore,
            assigned_to=outsider,
            created_by=integration_factory.user,
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            days_of_week=None,
            day_of_month=None,
            starts_at=datetime.date.today(),
            ends_at=None,
            db_session=db_session,
        )
        with pytest.raises(ValueError, match="family"):
            await svc.run_process()


# ══════════════════════════════════════════════════════════════════════════════
# 8. CreateQuickPlannedChore / CompleteQuickPlannedChore
#    UncompleteQuickPlannedChore / DeleteQuickPlannedChore
# ══════════════════════════════════════════════════════════════════════════════


class TestCreateQuickPlannedChore:
    """Integration tests for CreateQuickPlannedChore."""

    async def test_creates_quick_chore_in_db(self, db_session, integration_factory):
        """Service must persist a QuickPlannedChore."""
        from planned_chores.models import QuickPlannedChore
        from planned_chores.schemas import QuickPlannedChoreCreateSchema

        body = QuickPlannedChoreCreateSchema(
            name="Take out trash",
            valuation=5,
            due_date=datetime.date.today(),
        )
        svc = CreateQuickPlannedChore(
            body=body,
            current_user=integration_factory.user,
            assigned_to_user=integration_factory.user2,
            db_session=db_session,
        )
        qc = await svc.run_process()

        result = await db_session.execute(
            select(QuickPlannedChore).where(QuickPlannedChore.id == qc.id)
        )
        db_qc = result.scalar_one()
        assert db_qc.name == "Take out trash"
        assert db_qc.valuation == 5
        assert db_qc.family_id == integration_factory.user.family_id
        assert db_qc.assigned_to_id == integration_factory.user2.id
        assert db_qc.completed_by_id is None

    async def test_quick_chore_is_active_by_default(self, db_session, integration_factory):
        """Newly created quick chores must have is_active=True."""
        from planned_chores.schemas import QuickPlannedChoreCreateSchema

        body = QuickPlannedChoreCreateSchema(
            name="Active Task",
            valuation=3,
            due_date=datetime.date.today(),
        )
        svc = CreateQuickPlannedChore(
            body=body,
            current_user=integration_factory.user,
            assigned_to_user=None,
            db_session=db_session,
        )
        qc = await svc.run_process()
        assert qc.is_active is True


class TestCompleteQuickPlannedChore:
    """Integration tests for CompleteQuickPlannedChore."""

    async def test_sets_completed_by_id(self, db_session, integration_factory):
        """After completion, quick_planned_chore.completed_by_id must equal current_user.id."""
        qc = await integration_factory.create_quick_chore(due_date=datetime.date.today())
        user = integration_factory.user

        svc = CompleteQuickPlannedChore(
            quick_planned_chore=qc,
            current_user=user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(qc)
        assert qc.completed_by_id == user.id

    async def test_increments_user_experience(self, db_session, integration_factory):
        """Quick chore completion must add valuation to user.experience."""
        qc = await integration_factory.create_quick_chore(due_date=datetime.date.today())
        user = integration_factory.user
        initial_exp = user.experience

        svc = CompleteQuickPlannedChore(
            quick_planned_chore=qc,
            current_user=user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(user)
        assert user.experience == initial_exp + qc.valuation

    async def test_increments_family_experience(self, db_session, integration_factory):
        """Quick chore completion must add valuation to family.experience."""
        qc = await integration_factory.create_quick_chore(due_date=datetime.date.today())
        family = integration_factory.family
        initial_exp = family.experience

        svc = CompleteQuickPlannedChore(
            quick_planned_chore=qc,
            current_user=integration_factory.user,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(family)
        assert family.experience == initial_exp + qc.valuation

    async def test_raises_if_already_completed(self, db_session, integration_factory):
        """Completing an already-completed quick chore must raise ChoreCompletionCanNotBeChanged."""
        qc = await integration_factory.create_quick_chore(
            due_date=datetime.date.today(),
            completed_by=integration_factory.user,
        )

        svc = CompleteQuickPlannedChore(
            quick_planned_chore=qc,
            current_user=integration_factory.user,
            db_session=db_session,
        )
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await svc.run_process()


class TestUncompleteQuickPlannedChore:
    """Integration tests for UncompleteQuickPlannedChore."""

    async def test_clears_completed_by_id(self, db_session, integration_factory):
        """After uncomplete, completed_by_id must be None."""
        user = integration_factory.user
        user.experience = 100
        await db_session.flush()

        qc = await integration_factory.create_quick_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )

        svc = UncompleteQuickPlannedChore(quick_planned_chore=qc, db_session=db_session)
        await svc.run_process()

        await db_session.refresh(qc)
        assert qc.completed_by_id is None

    async def test_raises_if_not_completed(self, db_session, integration_factory):
        """Uncompleting a not-yet-completed quick chore must raise ChoreCompletionCanNotBeChanged."""
        qc = await integration_factory.create_quick_chore(due_date=datetime.date.today())

        svc = UncompleteQuickPlannedChore(quick_planned_chore=qc, db_session=db_session)
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await svc.run_process()


class TestDeleteQuickPlannedChore:
    """Integration tests for DeleteQuickPlannedChore."""

    async def test_soft_deletes_uncompleted_quick_chore(self, db_session, integration_factory):
        """Deleting an uncompleted quick chore should soft-delete it (is_active=False)."""
        from planned_chores.models import QuickPlannedChore

        qc = await integration_factory.create_quick_chore(due_date=datetime.date.today())
        qc_id = qc.id

        svc = DeleteQuickPlannedChore(
            quick_planned_chore_id=qc_id,
            db_session=db_session,
        )
        await svc.run_process()

        result = await db_session.execute(
            select(QuickPlannedChore).where(QuickPlannedChore.id == qc_id)
        )
        db_qc = result.scalar_one_or_none()
        assert db_qc is not None
        assert db_qc.is_active is False

    async def test_decrements_experience_on_completed_quick_chore_delete(
        self, db_session, integration_factory
    ):
        """Deleting a completed quick chore must decrement experience for user and family."""
        user = integration_factory.user
        family = integration_factory.family
        user.experience = 100
        family.experience = 100
        await db_session.flush()

        qc = await integration_factory.create_quick_chore(
            due_date=datetime.date.today(),
            completed_by=user,
        )
        valuation = qc.valuation
        qc_id = qc.id

        svc = DeleteQuickPlannedChore(
            quick_planned_chore_id=qc_id,
            db_session=db_session,
        )
        await svc.run_process()

        await db_session.refresh(user)
        await db_session.refresh(family)
        assert user.experience == 100 - valuation
        assert family.experience == 100 - valuation


# ══════════════════════════════════════════════════════════════════════════════
# 9. RecipeCreatorService / RecipeUpdateService
# ══════════════════════════════════════════════════════════════════════════════


class TestRecipeCreatorService:
    """Integration tests for RecipeCreatorService."""

    async def test_creates_recipe_in_db(self, db_session, integration_factory):
        """Service must persist a Recipe linked to the family."""
        from meals.models import Recipe

        data = RecipeCreateSchema(
            title="Spaghetti Bolognese",
            description="Classic Italian dish",
            category="dinner",
            prep_time_minutes=15,
            cook_time_minutes=45,
            base_servings=4,
            tags=["italian", "pasta"],
        )
        svc = RecipeCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        recipe = await svc.run_process()

        result = await db_session.execute(select(Recipe).where(Recipe.id == recipe.id))
        db_recipe = result.scalar_one()

        assert db_recipe.title == "Spaghetti Bolognese"
        assert db_recipe.family_id == integration_factory.family.id
        assert db_recipe.created_by_id == integration_factory.user.id
        assert db_recipe.category == "dinner"
        assert db_recipe.tags == ["italian", "pasta"]
        assert db_recipe.is_custom is True

    async def test_recipe_is_active_by_default(self, db_session, integration_factory):
        """Newly created recipes must have is_active=True."""
        data = RecipeCreateSchema(title="Active Recipe")
        svc = RecipeCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        recipe = await svc.run_process()
        assert recipe.is_active is True

    async def test_recipe_with_ingredients_and_steps(self, db_session, integration_factory):
        """Service must persist ingredients and steps as JSON."""
        from meals.schemas import IngredientSchema, RecipeStepSchema

        data = RecipeCreateSchema(
            title="Omelette",
            ingredients=[
                IngredientSchema(name="Eggs", amount=3, unit="pcs"),
                IngredientSchema(name="Salt", amount=None, unit="pinch"),
            ],
            steps=[
                RecipeStepSchema(number=1, text="Crack eggs"),
                RecipeStepSchema(number=2, text="Cook in pan"),
            ],
        )
        svc = RecipeCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        recipe = await svc.run_process()

        assert len(recipe.ingredients) == 2
        assert len(recipe.steps) == 2
        assert recipe.steps[0]["text"] == "Crack eggs"


class TestRecipeUpdateService:
    """Integration tests for RecipeUpdateService."""

    async def test_updates_recipe_title(self, db_session, integration_factory):
        """Service must persist title changes."""
        recipe = await integration_factory.create_recipe(title="Old Title")

        data = RecipeUpdateSchema(title="New Title")
        svc = RecipeUpdateService(recipe=recipe, data=data, db_session=db_session)
        updated = await svc.run_process()

        assert updated.title == "New Title"

    async def test_updates_recipe_category_and_tags(self, db_session, integration_factory):
        """Service must update category and tags independently."""
        recipe = await integration_factory.create_recipe(title="Tag Test Recipe")

        data = RecipeUpdateSchema(category="breakfast", tags=["healthy", "quick"])
        svc = RecipeUpdateService(recipe=recipe, data=data, db_session=db_session)
        updated = await svc.run_process()

        assert updated.category == "breakfast"
        assert updated.tags == ["healthy", "quick"]

    async def test_update_does_not_clear_unset_fields(self, db_session, integration_factory):
        """Fields not included in update payload must remain unchanged."""
        recipe = await integration_factory.create_recipe(title="Immutable Title Recipe")
        original_category = recipe.category

        data = RecipeUpdateSchema(cook_time_minutes=30)
        svc = RecipeUpdateService(recipe=recipe, data=data, db_session=db_session)
        updated = await svc.run_process()

        assert updated.cook_time_minutes == 30
        assert updated.category == original_category  # unchanged

    async def test_updates_recipe_ingredients(self, db_session, integration_factory):
        """Service must persist updated ingredient list."""
        from meals.schemas import IngredientSchema

        recipe = await integration_factory.create_recipe(title="Ingredient Update Recipe")

        new_ingredients = [IngredientSchema(name="Butter", amount=2, unit="tbsp")]
        data = RecipeUpdateSchema(ingredients=new_ingredients)
        svc = RecipeUpdateService(recipe=recipe, data=data, db_session=db_session)
        updated = await svc.run_process()

        assert len(updated.ingredients) == 1
        assert updated.ingredients[0]["name"] == "Butter"
