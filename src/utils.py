from datetime import UTC, datetime, timedelta
from statistics.schemas import DateRangeSchema
from calendar import monthrange


def get_current_week_range() -> DateRangeSchema:
    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return DateRangeSchema(start=monday, end=sunday)


def get_current_month_range() -> DateRangeSchema:
    today = datetime.now(UTC).date()
    first_day = today.replace(day=1)
    last_day = today.replace(day=monthrange(today.year, today.month)[1])

    return DateRangeSchema(start=first_day, end=last_day)
