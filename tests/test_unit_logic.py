"""
Unit tests for business logic validators, schemas, and the BaseService framework.

These tests do NOT require a database — they test pure logic in isolation.
"""

import datetime
import uuid

import pytest
from pydantic import ValidationError

from chores.models import Chore
from core.enums import FrequencyTypeENUM
from core.exceptions.chores_completion import ChoreCompletionCanNotBeChanged
from core.exceptions.families import UserIsAlreadyFamilyMember, UserNotFoundInFamily
from core.validators import (
    validate_date_is_not_in_past,
    validate_planned_chore_is_completed,
    validate_planned_chore_is_not_completed,
    validate_quick_planned_chore_is_completed,
    validate_quick_planned_chore_is_not_completed,
    validate_user_in_family,
    validate_user_not_in_family,
)
from planned_chores.models import PlannedChore, QuickPlannedChore
from users.models import User


# ── Validator Tests ───────────────────────────────────────────────────────────

class TestValidators:

    def _make_user(self, family_id=None) -> User:
        user = User()
        user.id = uuid.uuid4()
        user.family_id = family_id
        return user

    def _make_planned_chore(self, completed_by_id=None) -> PlannedChore:
        pc = PlannedChore()
        pc.id = uuid.uuid4()
        pc.completed_by_id = completed_by_id
        return pc

    def _make_quick_chore(self, completed_by_id=None) -> QuickPlannedChore:
        qc = QuickPlannedChore()
        qc.id = uuid.uuid4()
        qc.completed_by_id = completed_by_id
        return qc

    # validate_user_in_family

    def test_validate_user_in_family_passes_when_matching(self):
        family_id = uuid.uuid4()
        user = self._make_user(family_id=family_id)
        # Should not raise
        validate_user_in_family(user, family_id)

    def test_validate_user_in_family_raises_when_different(self):
        user = self._make_user(family_id=uuid.uuid4())
        with pytest.raises(UserNotFoundInFamily):
            validate_user_in_family(user, uuid.uuid4())

    def test_validate_user_in_family_raises_when_no_family(self):
        user = self._make_user(family_id=None)
        with pytest.raises(UserNotFoundInFamily):
            validate_user_in_family(user, uuid.uuid4())

    # validate_user_not_in_family

    def test_validate_user_not_in_family_passes_when_no_family(self):
        user = self._make_user(family_id=None)
        validate_user_not_in_family(user)

    def test_validate_user_not_in_family_raises_when_has_family(self):
        user = self._make_user(family_id=uuid.uuid4())
        with pytest.raises(UserIsAlreadyFamilyMember):
            validate_user_not_in_family(user)

    # validate_date_is_not_in_past

    def test_validate_date_not_in_past_passes_for_today(self):
        validate_date_is_not_in_past(datetime.date.today())

    def test_validate_date_not_in_past_passes_for_future(self):
        validate_date_is_not_in_past(datetime.date.today() + datetime.timedelta(days=5))

    def test_validate_date_not_in_past_raises_for_yesterday(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_date_is_not_in_past(yesterday)

    def test_validate_date_not_in_past_raises_for_old_date(self):
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_date_is_not_in_past(datetime.date(2020, 1, 1))

    # validate_planned_chore_is_completed

    def test_validate_planned_chore_is_completed_passes_when_completed(self):
        pc = self._make_planned_chore(completed_by_id=uuid.uuid4())
        validate_planned_chore_is_completed(pc)

    def test_validate_planned_chore_is_completed_raises_when_not_completed(self):
        pc = self._make_planned_chore(completed_by_id=None)
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_planned_chore_is_completed(pc)

    # validate_planned_chore_is_not_completed

    def test_validate_planned_chore_is_not_completed_passes_when_not_completed(self):
        pc = self._make_planned_chore(completed_by_id=None)
        validate_planned_chore_is_not_completed(pc)

    def test_validate_planned_chore_is_not_completed_raises_when_completed(self):
        pc = self._make_planned_chore(completed_by_id=uuid.uuid4())
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_planned_chore_is_not_completed(pc)

    # validate_quick_planned_chore_is_not_completed

    def test_validate_quick_not_completed_passes(self):
        qc = self._make_quick_chore(completed_by_id=None)
        validate_quick_planned_chore_is_not_completed(qc)

    def test_validate_quick_not_completed_raises_when_done(self):
        qc = self._make_quick_chore(completed_by_id=uuid.uuid4())
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_quick_planned_chore_is_not_completed(qc)

    # validate_quick_planned_chore_is_completed

    def test_validate_quick_is_completed_passes(self):
        qc = self._make_quick_chore(completed_by_id=uuid.uuid4())
        validate_quick_planned_chore_is_completed(qc)

    def test_validate_quick_is_completed_raises_when_not_done(self):
        qc = self._make_quick_chore(completed_by_id=None)
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            validate_quick_planned_chore_is_completed(qc)


# ── Schema Tests ──────────────────────────────────────────────────────────────

class TestChoreSchemas:

    def test_chore_create_schema_valid(self):
        from chores.schemas import ChoreCreateSchema
        schema = ChoreCreateSchema(
            name="Test",
            valuation=10,
            icon="some-icon",
            icon_color="#fff",
            icon_bg="#000",
        )
        assert schema.name == "Test"
        assert schema.valuation == 10

    def test_chore_create_schema_missing_required_fields(self):
        from chores.schemas import ChoreCreateSchema
        with pytest.raises(ValidationError):
            ChoreCreateSchema()

    def test_chore_update_schema_partial(self):
        from chores.schemas import ChoreUpdateSchema
        schema = ChoreUpdateSchema(name="Updated")
        data = schema.model_dump(exclude_unset=True)
        assert "name" in data
        assert "valuation" not in data


class TestPlannedChoreSchemas:

    def test_planned_chore_create_schema_valid(self):
        from planned_chores.schemas import PlannedChoreCreateSchema
        schema = PlannedChoreCreateSchema(
            chore_id=uuid.uuid4(),
            due_date=datetime.date.today(),
            message="",
        )
        assert schema.due_date == datetime.date.today()

    def test_chore_schedule_create_schema(self):
        from planned_chores.schemas import ChoreScheduleCreateSchema
        schema = ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=datetime.date.today(),
        )
        assert schema.frequency_type == FrequencyTypeENUM.daily

    def test_chore_schedule_invalid_frequency(self):
        from planned_chores.schemas import ChoreScheduleCreateSchema
        with pytest.raises(ValidationError):
            ChoreScheduleCreateSchema(
                assigned_to_id=uuid.uuid4(),
                frequency_type="hourly",  # not in enum
                interval=1,
                starts_at=datetime.date.today(),
            )


class TestMealSchemas:

    def test_recipe_create_schema_defaults(self):
        from meals.schemas import RecipeCreateSchema
        schema = RecipeCreateSchema(
            title="Quick Salad",
            ingredients=[],
            steps=[],
        )
        assert schema.title == "Quick Salad"
        assert schema.category == "quick"
        assert schema.base_servings == 4

    def test_recipe_create_rejects_empty_title(self):
        from meals.schemas import RecipeCreateSchema
        with pytest.raises(ValidationError):
            RecipeCreateSchema(title="", ingredients=[], steps=[])

    def test_planned_meal_create_schema(self):
        from meals.schemas import PlannedMealCreateSchema
        schema = PlannedMealCreateSchema(
            date=datetime.date.today(),
            slot="lunch",
            title="Pasta",
        )
        assert schema.slot == "lunch"

    def test_planned_meal_invalid_slot(self):
        from meals.schemas import PlannedMealCreateSchema
        with pytest.raises(ValidationError):
            PlannedMealCreateSchema(
                date=datetime.date.today(),
                slot="midnight_snack",  # invalid slot
                title="Pizza",
            )


class TestAuthSchemas:

    def test_register_schema_validates_password(self):
        from auth.schemas import RegisterSchema
        with pytest.raises(ValidationError):
            RegisterSchema(username="te", password="ab")  # too short username AND password

    def test_login_schema_valid(self):
        from auth.schemas import LoginSchema
        schema = LoginSchema(username="alice", password="anypassword")
        assert schema.username == "alice"

    def test_register_schema_valid(self):
        from auth.schemas import RegisterSchema
        schema = RegisterSchema(username="alice123", password="Passw0rd!")
        assert schema.username == "alice123"


# ── BaseService Framework Tests ───────────────────────────────────────────────

class TestBaseService:

    async def test_base_service_calls_validators_before_process(self):
        from core.services import BaseService

        calls = []

        class MyService(BaseService[str]):
            def get_validators(self):
                return [lambda: calls.append("validated")]

            async def process(self) -> str:
                calls.append("processed")
                return "done"

        service = MyService()
        result = await service.run_process()
        assert result == "done"
        assert calls == ["validated", "processed"]

    async def test_base_service_raises_before_process_on_failed_validator(self):
        from core.services import BaseService

        processed = []

        class MyService(BaseService[str]):
            def get_validators(self):
                return [
                    lambda: (_ for _ in ()).throw(ValueError("invalid!"))
                ]

            async def process(self) -> str:
                processed.append("processed")
                return "done"

        service = MyService()
        with pytest.raises(Exception):
            await service.run_process()
        assert processed == []  # process was never called

    async def test_base_service_without_validators_runs_process(self):
        from core.services import BaseService

        class SimpleService(BaseService[int]):
            async def process(self) -> int:
                return 42

        service = SimpleService()
        result = await service.run_process()
        assert result == 42

    async def test_base_service_multiple_validators_all_run(self):
        from core.services import BaseService

        log = []

        class MultiValidatorService(BaseService[None]):
            def get_validators(self):
                return [
                    lambda: log.append(1),
                    lambda: log.append(2),
                    lambda: log.append(3),
                ]

            async def process(self):
                log.append("done")

        service = MultiValidatorService()
        await service.run_process()
        assert log == [1, 2, 3, "done"]


# ── FrequencyTypeENUM Tests ───────────────────────────────────────────────────

class TestFrequencyTypeEnum:

    def test_enum_values(self):
        assert FrequencyTypeENUM.daily.value == "daily"
        assert FrequencyTypeENUM.weekly.value == "weekly"
        assert FrequencyTypeENUM.monthly.value == "monthly"

    def test_enum_name(self):
        assert FrequencyTypeENUM.get_enum_name() == "frequency_type"

    def test_enum_from_value(self):
        assert FrequencyTypeENUM("daily") == FrequencyTypeENUM.daily


# ── Hasher Unit Tests ─────────────────────────────────────────────────────────

class TestHasherUnit:

    def test_hash_and_verify_roundtrip(self):
        from core.hashing import Hasher
        pw = "MySecure!Password123"
        hashed = Hasher.get_password_hash(pw)
        assert Hasher.verify_password(pw, hashed)

    def test_different_passwords_do_not_match(self):
        from core.hashing import Hasher
        hashed = Hasher.get_password_hash("Correct1!")
        assert not Hasher.verify_password("Wrong1!", hashed)

    def test_hash_is_not_plaintext(self):
        from core.hashing import Hasher
        pw = "MySecure!Password123"
        assert Hasher.get_password_hash(pw) != pw


# ── Timezone Utilities Unit Tests ─────────────────────────────────────────────

class TestTimezoneUtilities:

    def test_resolve_timezone(self):
        from utils import resolve_timezone
        from zoneinfo import ZoneInfo
        assert resolve_timezone("Europe/Moscow") == ZoneInfo("Europe/Moscow")
        assert resolve_timezone("UTC") == ZoneInfo("UTC")
        assert resolve_timezone("Invalid/Timezone") == ZoneInfo("UTC")
        assert resolve_timezone(None) == ZoneInfo("UTC")

    def test_get_user_now_and_today(self):
        import datetime
        from utils import get_user_now, get_user_today
        now_moscow = get_user_now("Europe/Moscow")
        assert now_moscow.tzinfo is not None
        assert str(now_moscow.tzinfo) == "Europe/Moscow"

        today_moscow = get_user_today("Europe/Moscow")
        assert isinstance(today_moscow, datetime.date)

    def test_get_current_week_and_month_range(self):
        from utils import get_current_week_range, get_current_month_range
        week = get_current_week_range("Europe/Moscow")
        assert week.start.weekday() == 0  # Monday
        assert week.end.weekday() == 6    # Sunday
        assert (week.end - week.start).days == 6

        month = get_current_month_range("Europe/Moscow")
        assert month.start.day == 1
        assert month.end.day >= 28

    def test_get_request_timezone_header(self):
        from utils import get_request_timezone
        assert get_request_timezone("Europe/Moscow") == "Europe/Moscow"
        assert get_request_timezone("Asia/Tokyo") == "Asia/Tokyo"
        assert get_request_timezone("Garbage") == "UTC"
        assert get_request_timezone(None) == "UTC"

