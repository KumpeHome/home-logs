from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.timezones import (
    format_clock_12h,
    iso_utc,
    local_date,
    local_time_hm,
    range_end_utc,
    range_start_utc,
    to_utc_naive,
)


def test_chicago_evening_converts_from_utc() -> None:
    stored = datetime(2026, 8, 30, 1, 27)
    assert local_date(stored, "America/Chicago") == date(2026, 8, 29)
    assert local_time_hm(stored, "America/Chicago") == "8:27 PM"


def test_format_clock_12h_from_24h_string() -> None:
    assert format_clock_12h("16:30") == "4:30 PM"
    assert format_clock_12h("16:30:00") == "4:30 PM"
    assert format_clock_12h("09:05") == "9:05 AM"


def test_iso_utc_marks_naive_storage_as_utc() -> None:
    assert iso_utc(datetime(2026, 8, 30, 1, 27)).endswith("Z")


def test_to_utc_naive_converts_offset_before_stripping() -> None:
    local = datetime(2026, 8, 29, 20, 27, tzinfo=ZoneInfo("America/Chicago"))
    assert to_utc_naive(local) == datetime(2026, 8, 30, 1, 27)


def test_date_range_uses_household_midnight() -> None:
    start = range_start_utc(date(2026, 8, 29), "America/Chicago")
    end = range_end_utc(date(2026, 8, 29), "America/Chicago")
    occurred = datetime(2026, 8, 30, 1, 27)
    assert start is not None and end is not None
    assert start <= occurred < end
    assert start != datetime(2026, 8, 29, 0, 0)
