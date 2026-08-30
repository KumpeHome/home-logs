from datetime import date

from app.services.med_rules import is_administerable


def test_medication_without_dates_is_administerable_when_active() -> None:
    assert is_administerable(
        active=True, start_date=None, end_date=None, on=date(2026, 8, 19)
    )


def test_medication_outside_start_end_window_is_not_administerable() -> None:
    assert not is_administerable(
        active=True,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        on=date(2026, 8, 19),
    )


def test_inactive_medication_is_not_administerable() -> None:
    assert not is_administerable(
        active=False, start_date=None, end_date=None, on=date(2026, 8, 19)
    )
