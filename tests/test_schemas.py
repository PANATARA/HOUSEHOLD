import datetime
import uuid
import pytest
from pydantic import ValidationError

from core.enums import FrequencyTypeENUM
from planned_chores.schemas import (
    ChoreScheduleCreateSchema,
    ChoreScheduleUpdateSchema,
    ChoreScheduleResponseSchema,
)


def test_valid_daily_schedule_schema():
    today = datetime.date.today()
    schema = ChoreScheduleCreateSchema(
        assigned_to_id=uuid.uuid4(),
        frequency_type=FrequencyTypeENUM.daily,
        interval=1,
        starts_at=today,
    )
    assert schema.frequency_type == FrequencyTypeENUM.daily
    assert schema.interval == 1
    assert schema.starts_at == today
    assert schema.ends_at is None
    assert schema.days_of_week is None
    assert schema.day_of_month is None


def test_valid_weekly_schedule_schema():
    today = datetime.date.today()
    # bitmask 21 = 1 (Mon) | 4 (Wed) | 16 (Fri)
    schema = ChoreScheduleCreateSchema(
        assigned_to_id=uuid.uuid4(),
        frequency_type=FrequencyTypeENUM.weekly,
        interval=2,
        days_of_week=21,
        starts_at=today,
    )
    assert schema.frequency_type == FrequencyTypeENUM.weekly
    assert schema.days_of_week == 21
    assert schema.interval == 2


def test_weekly_schedule_requires_days_of_week():
    today = datetime.date.today()
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.weekly,
            interval=1,
            days_of_week=None,
            starts_at=today,
        )
    assert "days_of_week is required for weekly frequency" in str(exc_info.value)


def test_weekly_schedule_bitmask_out_of_bounds():
    today = datetime.date.today()
    # Bitmask must be between 1 and 127
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.weekly,
            interval=1,
            days_of_week=128,
            starts_at=today,
        )
    assert "days_of_week bitmask must be between 1 and 127" in str(exc_info.value)


def test_valid_monthly_schedule_schema():
    today = datetime.date.today()
    schema = ChoreScheduleCreateSchema(
        assigned_to_id=uuid.uuid4(),
        frequency_type=FrequencyTypeENUM.monthly,
        interval=1,
        day_of_month=15,
        starts_at=today,
    )
    assert schema.frequency_type == FrequencyTypeENUM.monthly
    assert schema.day_of_month == 15


def test_monthly_schedule_requires_day_of_month():
    today = datetime.date.today()
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.monthly,
            interval=1,
            day_of_month=None,
            starts_at=today,
        )
    assert "day_of_month is required for monthly frequency" in str(exc_info.value)


def test_monthly_schedule_day_out_of_bounds():
    today = datetime.date.today()
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.monthly,
            interval=1,
            day_of_month=32,
            starts_at=today,
        )
    assert "day_of_month must be between 1 and 31" in str(exc_info.value)


def test_schedule_ends_at_before_starts_at():
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.daily,
            interval=1,
            starts_at=today,
            ends_at=yesterday,
        )
    assert "ends_at cannot be before starts_at" in str(exc_info.value)


def test_schedule_invalid_interval():
    today = datetime.date.today()
    with pytest.raises(ValidationError):
        ChoreScheduleCreateSchema(
            assigned_to_id=uuid.uuid4(),
            frequency_type=FrequencyTypeENUM.daily,
            interval=0,
            starts_at=today,
        )


def test_update_schema_partial_valid():
    update = ChoreScheduleUpdateSchema(interval=3)
    assert update.interval == 3
    assert update.frequency_type is None
    assert update.days_of_week is None


def test_update_schema_switch_to_weekly_requires_days():
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleUpdateSchema(
            frequency_type=FrequencyTypeENUM.weekly,
            days_of_week=None,
        )
    assert "days_of_week is required for weekly frequency" in str(exc_info.value)


def test_update_schema_switch_to_monthly_requires_day():
    with pytest.raises(ValidationError) as exc_info:
        ChoreScheduleUpdateSchema(
            frequency_type=FrequencyTypeENUM.monthly,
            day_of_month=None,
        )
    assert "day_of_month is required for monthly frequency" in str(exc_info.value)


def test_response_schema_validation():
    sched_id = uuid.uuid4()
    chore_id = uuid.uuid4()
    family_id = uuid.uuid4()
    user_id = uuid.uuid4()
    today = datetime.date.today()

    data = {
        "id": sched_id,
        "chore_id": chore_id,
        "family_id": family_id,
        "assigned_to_id": user_id,
        "frequency_type": FrequencyTypeENUM.daily,
        "interval": 1,
        "days_of_week": None,
        "day_of_month": None,
        "starts_at": today,
        "ends_at": None,
        "last_generated_until": None,
        "is_active": True,
        "created_by": user_id,
    }
    response = ChoreScheduleResponseSchema.model_validate(data)
    assert response.id == sched_id
    assert response.frequency_type == FrequencyTypeENUM.daily
    assert response.is_active is True


def test_planned_chore_update_message_schema_valid():
    from planned_chores.schemas import PlannedChoreUpdateMessageSchema, PlannedChoreUpdateSchema

    schema = PlannedChoreUpdateMessageSchema(message="New custom note")
    assert schema.message == "New custom note"

    alias_schema = PlannedChoreUpdateSchema(message="Alias note")
    assert alias_schema.message == "Alias note"


def test_planned_chore_update_message_schema_max_length():
    from planned_chores.schemas import PlannedChoreUpdateMessageSchema

    with pytest.raises(ValidationError):
        PlannedChoreUpdateMessageSchema(message="a" * 2001)


def test_planned_chore_update_message_schema_required():
    from planned_chores.schemas import PlannedChoreUpdateMessageSchema

    with pytest.raises(ValidationError):
        PlannedChoreUpdateMessageSchema()  # missing message

