from datetime import UTC, datetime, timedelta
from statistics.schemas import DateRangeSchema


def get_current_week_range() -> DateRangeSchema:
    today = datetime.now(UTC).date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return DateRangeSchema(start=monday, end=sunday)
