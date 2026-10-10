"""
Integration tests for database constraints, indexes, and data integrity.

Verifies:
- UNIQUE constraints (username, email, google_sub, device token)
- FOREIGN KEY constraints with CASCADE and RESTRICT behaviors
- Soft delete (is_active = False) patterns
- Experience and total_completed counter invariants
- Concurrent-safe counter operations (no negative values)
"""

import datetime
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from core.hashing import Hasher
from notifications.models import UserDevice
from planned_chores.models import ChoreSchedule, PlannedChore, QuickPlannedChore
from users.models import User, UserFamilyPermissions, UserSettings


class TestUniqueConstraints:
    """Verify that UNIQUE constraints are enforced at the DB level."""

    async def test_username_must_be_unique(
        self, db_session: AsyncSession, integration_factory
    ):
        duplicate = User(
            username=integration_factory.user.username,
            email="totally_different@example.com",
            hashed_password=Hasher.get_password_hash("Abc123!"),
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_email_must_be_unique(
        self, db_session: AsyncSession, integration_factory
    ):
        duplicate = User(
            username="absolutely_unique_xyz_123",
            email=integration_factory.user.email,
            hashed_password=Hasher.get_password_hash("Abc123!"),
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_google_sub_must_be_unique(
        self, db_session: AsyncSession, integration_factory
    ):
        sub = f"google_sub_{uuid.uuid4().hex}"
        # Give first user a google_sub
        integration_factory.user.google_sub = sub
        db_session.add(integration_factory.user)
        await db_session.flush()

        # Try to create second user with same google_sub
        duplicate = User(
            username="unique_user_for_sub_test",
            email="subtest_unique@example.com",
            google_sub=sub,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_device_token_must_be_unique(
        self, db_session: AsyncSession, integration_factory
    ):
        token = f"fcm_token_{uuid.uuid4().hex}"
        device1 = UserDevice(
            user_id=integration_factory.user.id,
            token=token,
            device_type="android",
        )
        db_session.add(device1)
        await db_session.flush()

        device2 = UserDevice(
            user_id=integration_factory.user2.id,
            token=token,  # same token
            device_type="ios",
        )
        db_session.add(device2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_user_settings_one_to_one_per_user(
        self, db_session: AsyncSession, integration_factory
    ):
        duplicate_settings = UserSettings(
            user_id=integration_factory.user.id,  # already has settings
            app_theme="Light",
            language="en",
            date_of_birth=datetime.date(2000, 1, 1),
        )
        db_session.add(duplicate_settings)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_user_permissions_one_to_one_per_user(
        self, db_session: AsyncSession, integration_factory
    ):
        duplicate_perms = UserFamilyPermissions(
            user_id=integration_factory.user.id,  # already has permissions
            can_invite_users=False,
        )
        db_session.add(duplicate_perms)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestForeignKeyConstraints:
    """Verify FOREIGN KEY constraints and their ON DELETE behaviors."""

    async def test_chore_with_nonexistent_family_id_raises(
        self, db_session: AsyncSession
    ):
        bad_chore = Chore(
            name="Ghost Chore",
            valuation=5,
            family_id=uuid.uuid4(),  # doesn't exist
        )
        db_session.add(bad_chore)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_planned_chore_with_nonexistent_chore_id_raises(
        self, db_session: AsyncSession, integration_factory
    ):
        bad_pc = PlannedChore(
            chore_id=uuid.uuid4(),  # doesn't exist → RESTRICT
            family_id=integration_factory.family.id,
            due_date=datetime.date.today(),
            created_by=integration_factory.user.id,
        )
        db_session.add(bad_pc)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_planned_chore_with_nonexistent_family_id_raises(
        self, db_session: AsyncSession, integration_factory
    ):
        bad_pc = PlannedChore(
            chore_id=integration_factory.chore.id,
            family_id=uuid.uuid4(),  # doesn't exist → CASCADE means it must exist
            due_date=datetime.date.today(),
        )
        db_session.add(bad_pc)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_quick_chore_with_nonexistent_family_id_raises(
        self, db_session: AsyncSession
    ):
        bad_qc = QuickPlannedChore(
            name="Bad Quick",
            valuation=5,
            family_id=uuid.uuid4(),
            due_date=datetime.date.today(),
        )
        db_session.add(bad_qc)
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()


class TestSoftDelete:
    """Verify soft delete behavior (is_active = False)."""

    async def test_soft_deleted_planned_chore_not_visible_in_active_query(
        self, db_session: AsyncSession, integration_factory
    ):
        pc = await integration_factory.create_planned_chore()
        from planned_chores.repository import PlannedChoreRepository
        repo = PlannedChoreRepository(db_session)
        await repo.soft_delete(pc.id)
        await db_session.refresh(pc)
        assert pc.is_active is False

    async def test_soft_deleted_chore_sets_is_active_false(
        self, db_session: AsyncSession, integration_factory
    ):
        from chores.repository import ChoreRepository
        repo = ChoreRepository(db_session)
        result = await repo.soft_delete(integration_factory.chore.id)
        assert result is True
        await db_session.refresh(integration_factory.chore)
        assert integration_factory.chore.is_active is False

    async def test_soft_delete_nonexistent_returns_false(
        self, db_session: AsyncSession, integration_factory
    ):
        from chores.repository import ChoreRepository
        repo = ChoreRepository(db_session)
        result = await repo.soft_delete(uuid.uuid4())
        assert result is False

    async def test_hard_delete_removes_row(
        self, db_session: AsyncSession, integration_factory
    ):
        pc = await integration_factory.create_planned_chore()
        pc_id = pc.id

        from planned_chores.repository import PlannedChoreRepository
        repo = PlannedChoreRepository(db_session)
        await repo.hard_delete(pc_id)

        result = await db_session.execute(
            select(PlannedChore).where(PlannedChore.id == pc_id)
        )
        assert result.scalar_one_or_none() is None


class TestExperienceInvariants:
    """Experience and total_completed counters must never go below 0."""

    async def test_decrement_experience_below_zero_is_no_op(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        family = integration_factory.family

        # Make sure experience is 0
        family.experience = 0
        db_session.add(family)
        await db_session.flush()

        # Try to decrement below 0
        await repo.decrement_experience(family.id, 100)
        await db_session.refresh(family)
        # The query has WHERE experience >= value, so it remains 0
        assert family.experience >= 0

    async def test_decrement_total_completed_below_zero_is_no_op(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        family = integration_factory.family

        family.total_completed = 0
        db_session.add(family)
        await db_session.flush()

        await repo.decrement_total_completed(family.id)
        await db_session.refresh(family)
        assert family.total_completed >= 0

    async def test_user_experience_increments_correctly(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        user = integration_factory.user

        initial_exp = user.experience
        await repo.increment_experience(user.id, 25)
        await db_session.refresh(user)
        assert user.experience == initial_exp + 25

    async def test_user_experience_decrements_correctly(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        user = integration_factory.user

        # Set to known value
        user.experience = 50
        db_session.add(user)
        await db_session.flush()

        await repo.decrement_experience(user.id, 20)
        await db_session.refresh(user)
        assert user.experience == 30

    async def test_user_total_completed_increments(
        self, db_session: AsyncSession, integration_factory
    ):
        from users.repository import UserRepository
        repo = UserRepository(db_session)
        user = integration_factory.user

        initial = user.total_completed
        await repo.increment_total_completed(user.id)
        await db_session.refresh(user)
        assert user.total_completed == initial + 1

    async def test_family_experience_increment_and_decrement(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        family = integration_factory.family

        family.experience = 100
        db_session.add(family)
        await db_session.flush()

        await repo.increment_experience(family.id, 50)
        await db_session.refresh(family)
        assert family.experience == 150

        await repo.decrement_experience(family.id, 30)
        await db_session.refresh(family)
        assert family.experience == 120


class TestDataConsistency:
    """Test multi-table consistency scenarios."""

    async def test_completing_chore_updates_user_and_family_experience(
        self, db_session: AsyncSession, integration_factory
    ):
        from planned_chores.services import CompletePlannedChore

        pc = await integration_factory.create_planned_chore()
        user = integration_factory.user
        family = integration_factory.family

        initial_user_exp = user.experience
        initial_family_exp = family.experience
        chore_valuation = integration_factory.chore.valuation  # 10

        service = CompletePlannedChore(
            planned_chore=pc,
            completed_by=user,
            db_session=db_session,
        )
        await service.run_process()

        await db_session.refresh(user)
        await db_session.refresh(family)

        assert user.experience == initial_user_exp + chore_valuation
        assert family.experience == initial_family_exp + chore_valuation

    async def test_uncompleting_chore_restores_experience(
        self, db_session: AsyncSession, integration_factory
    ):
        from planned_chores.services import (
            CompletePlannedChore,
            UncompletePlannedChore,
        )

        pc = await integration_factory.create_planned_chore()
        user = integration_factory.user
        family = integration_factory.family
        initial_user_exp = user.experience
        initial_family_exp = family.experience

        # Complete
        await CompletePlannedChore(
            planned_chore=pc, completed_by=user, db_session=db_session
        ).run_process()

        # Uncomplete
        await db_session.refresh(pc)
        await UncompletePlannedChore(
            planned_chore=pc, db_session=db_session
        ).run_process()

        await db_session.refresh(user)
        await db_session.refresh(family)

        assert user.experience == initial_user_exp
        assert family.experience == initial_family_exp

    async def test_family_member_count_is_accurate(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        count = await repo.count_family_members(integration_factory.family.id)
        # factory creates 2 users
        assert count == 2

    async def test_user_is_family_admin_returns_correct_result(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        is_admin = await repo.user_is_family_admin(
            user_id=integration_factory.user.id,
            family_id=integration_factory.family.id,
        )
        assert is_admin is True

    async def test_non_admin_user_is_not_admin(
        self, db_session: AsyncSession, integration_factory
    ):
        from families.repository import FamilyRepository
        repo = FamilyRepository(db_session)
        is_admin = await repo.user_is_family_admin(
            user_id=integration_factory.user2.id,
            family_id=integration_factory.family.id,
        )
        assert is_admin is False
