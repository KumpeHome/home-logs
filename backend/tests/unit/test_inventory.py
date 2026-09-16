from datetime import date
from types import SimpleNamespace

from app.models import HouseholdOtcMedication, Medication
from app.services.inventory import (
    apply_refill,
    consume_administered_dose,
    locked_get,
    needs_refill,
    remaining_after_dose,
    remaining_refills_after_fill,
)


def test_needs_refill_when_on_hand_at_or_below_reminder_level() -> None:
    assert needs_refill(quantity_on_hand=8, refill_reminder_level=10)
    assert needs_refill(quantity_on_hand=10, refill_reminder_level=10)
    assert not needs_refill(quantity_on_hand=11, refill_reminder_level=10)


def test_needs_refill_is_false_when_stock_is_not_tracked() -> None:
    assert not needs_refill(quantity_on_hand=None, refill_reminder_level=10)
    assert not needs_refill(quantity_on_hand=4, refill_reminder_level=None)


def test_dose_decrements_tracked_stock_and_does_not_go_below_zero() -> None:
    assert remaining_after_dose(12, 2) == 10
    assert remaining_after_dose(1, 3) == 0
    assert remaining_after_dose(None, 1) is None


def test_refill_adds_quantity_and_decrements_remaining_fills() -> None:
    on_hand, remaining = apply_refill(
        quantity_on_hand=4,
        refill_quantity=30,
        refills_remaining=2,
        filled_on=date(2026, 9, 14),
    )
    assert on_hand == 34
    assert remaining == 1

    on_hand, remaining = apply_refill(
        quantity_on_hand=None,
        refill_quantity=30,
        refills_remaining=None,
        filled_on=date(2026, 9, 14),
    )
    assert on_hand == 30
    assert remaining is None


def test_refills_remaining_does_not_go_below_zero() -> None:
    assert remaining_refills_after_fill(0) == 0
    assert remaining_refills_after_fill(1) == 0
    assert remaining_refills_after_fill(None) is None


def test_locked_get_refreshes_row_with_for_update() -> None:
    calls: dict = {}

    class FakeDb:
        def get(self, model, ident, **kwargs):
            calls["model"] = model
            calls["ident"] = ident
            calls["kwargs"] = kwargs
            return SimpleNamespace(id=ident)

    row = locked_get(FakeDb(), Medication, "med-1")
    assert row.id == "med-1"
    assert calls["model"] is Medication
    assert calls["ident"] == "med-1"
    assert calls["kwargs"]["with_for_update"] is True
    assert calls["kwargs"]["populate_existing"] is True


def test_consume_administered_dose_locks_the_inventory_row(monkeypatch) -> None:
    med = SimpleNamespace(id="med-1", quantity_on_hand=10)
    locked: list[tuple] = []

    def fake_locked_get(db, model, ident):
        locked.append((model, ident))
        assert model is Medication
        return med

    monkeypatch.setattr("app.services.inventory.locked_get", fake_locked_get)
    consume_administered_dose(
        SimpleNamespace(),
        "h1",
        {"medication_id": "med-1", "quantity_given": 2, "outcome": "given"},
        submitted=True,
    )
    assert locked == [(Medication, "med-1")]
    assert med.quantity_on_hand == 8


def test_consume_administered_dose_locks_household_otc_row(monkeypatch) -> None:
    otc = SimpleNamespace(id="otc-1", quantity_on_hand=6, household_id="h1")
    locked: list[tuple] = []

    def fake_locked_get(db, model, ident):
        locked.append((model, ident))
        if model is Medication:
            return None
        return otc

    monkeypatch.setattr("app.services.inventory.locked_get", fake_locked_get)
    consume_administered_dose(
        SimpleNamespace(get=lambda *_args, **_kwargs: None),
        "h1",
        {"medication_id": "otc-1", "quantity_given": 1, "outcome": "given"},
        submitted=True,
    )
    assert (HouseholdOtcMedication, "otc-1") in locked
    assert otc.quantity_on_hand == 5
