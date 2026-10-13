from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Header

from statistics.schemas import DateRangeSchema


def resolve_timezone(tz_name: str | None = None) -> ZoneInfo:
    """Resolve an IANA timezone name safely, falling back to UTC."""
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return ZoneInfo("UTC")


def get_user_now(tz_name: str | None = None) -> datetime:
    """Return current datetime in the specified or default (UTC) timezone."""
    return datetime.now(resolve_timezone(tz_name))


def get_user_today(tz_name: str | None = None) -> date:
    """Return current date in the specified or default (UTC) timezone."""
    return get_user_now(tz_name).date()


def get_current_week_range(tz_name: str | None = None) -> DateRangeSchema:
    today = get_user_today(tz_name)
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    return DateRangeSchema(start=monday, end=sunday)


def get_current_month_range(tz_name: str | None = None) -> DateRangeSchema:
    today = get_user_today(tz_name)
    first_day = today.replace(day=1)
    last_day = today.replace(day=monthrange(today.year, today.month)[1])

    return DateRangeSchema(start=first_day, end=last_day)


def get_request_timezone(
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
) -> str:
    """
    Extract and validate client's timezone from the X-Timezone header.
    Returns the validated IANA timezone string or 'UTC'.
    """
    if x_timezone:
        try:
            ZoneInfo(x_timezone)
            return x_timezone
        except Exception:
            pass
    return "UTC"


SUPPORTED_LANGUAGES = {"ru", "en"}
DEFAULT_LANGUAGE = "ru"


def resolve_language(lang_code: str | None = None) -> str:
    """
    Resolve requested language code to a supported language ('ru' or 'en').
    Accepts full codes like 'en-US', 'ru-RU', or simple 'en', 'ru'.
    Parses comma-separated Accept-Language values as well.
    Defaults to 'ru'.
    """
    if not lang_code:
        return DEFAULT_LANGUAGE

    for part in lang_code.split(","):
        tag = part.split(";")[0].strip().lower()
        primary = tag.split("-")[0].strip()
        if primary in SUPPORTED_LANGUAGES:
            return primary

    return DEFAULT_LANGUAGE


def get_request_language(
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> str:
    """
    FastAPI dependency to extract and resolve language from Accept-Language header.
    Defaults to 'ru'.
    """
    return resolve_language(accept_language)

