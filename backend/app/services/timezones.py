from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "America/Chicago"


def zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TZ)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TZ)


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def from_utc_naive(value: datetime, tz_name: str | None) -> datetime:
    utc = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return utc.astimezone(zone(tz_name))


def iso_utc(value: datetime) -> str:
    return f"{to_utc_naive(value).isoformat()}Z"


def local_date(value: datetime, tz_name: str | None) -> date:
    return from_utc_naive(value, tz_name).date()


def local_time_hm(value: datetime, tz_name: str | None) -> str:
    return from_utc_naive(value, tz_name).strftime("%I:%M %p").lstrip("0")


def format_clock_12h(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return text
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def range_start_utc(
    value: date | datetime | None, tz_name: str | None
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_utc_naive(value)
    start = datetime.combine(value, time.min, tzinfo=zone(tz_name))
    return start.astimezone(UTC).replace(tzinfo=None)


def range_end_utc(
    value: date | datetime | None, tz_name: str | None
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_utc_naive(value)
    end = datetime.combine(value + timedelta(days=1), time.min, tzinfo=zone(tz_name))
    return end.astimezone(UTC).replace(tzinfo=None)
