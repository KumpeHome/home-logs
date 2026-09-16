from __future__ import annotations

from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import HouseholdOtcMedication, Medication, MemberOtcAssignment


class StockRecord(Protocol):
    quantity_on_hand: float | None
    refill_quantity: float | None
    refill_reminder_level: float | None
    last_refill_on: date | None


def needs_refill(
    *,
    quantity_on_hand: float | None,
    refill_reminder_level: float | None,
) -> bool:
    if quantity_on_hand is None or refill_reminder_level is None:
        return False
    return quantity_on_hand <= refill_reminder_level


def remaining_after_dose(
    quantity_on_hand: float | None, quantity_given: float
) -> float | None:
    if quantity_on_hand is None:
        return None
    leftover = quantity_on_hand - quantity_given
    return max(0.0, leftover)


def remaining_refills_after_fill(refills_remaining: int | None) -> int | None:
    if refills_remaining is None:
        return None
    return max(0, refills_remaining - 1)


def apply_refill(
    *,
    quantity_on_hand: float | None,
    refill_quantity: float,
    refills_remaining: int | None,
    filled_on: date,
) -> tuple[float, int | None]:
    del filled_on
    current = 0.0 if quantity_on_hand is None else quantity_on_hand
    return current + refill_quantity, remaining_refills_after_fill(refills_remaining)


def requested_refill_quantity(item: StockRecord, quantity: float | None) -> float:
    amount = item.refill_quantity if quantity is None else quantity
    if amount is None or amount <= 0:
        raise DomainError("Set a refill quantity before recording a refill")
    return float(amount)


def locked_get[T](db: Session, model: type[T], ident: str) -> T | None:
    return db.get(model, ident, with_for_update=True, populate_existing=True)


def consume_stock(item: StockRecord, quantity_given: float) -> None:
    item.quantity_on_hand = remaining_after_dose(item.quantity_on_hand, quantity_given)


def fill_stock(
    item: StockRecord,
    *,
    refill_quantity: float,
    filled_on: date,
) -> None:
    remaining = getattr(item, "refills_remaining", None)
    on_hand, leftover = apply_refill(
        quantity_on_hand=item.quantity_on_hand,
        refill_quantity=refill_quantity,
        refills_remaining=remaining,
        filled_on=filled_on,
    )
    item.quantity_on_hand = on_hand
    item.last_refill_on = filled_on
    if hasattr(item, "refills_remaining"):
        item.refills_remaining = leftover


def stock_for_administered_id(
    db: Session, household_id: str, medication_id: str | None
) -> StockRecord | None:
    if not medication_id:
        return None
    med = locked_get(db, Medication, medication_id)
    if med is not None:
        return med
    return _household_otc(db, household_id, medication_id)


def _household_otc(
    db: Session, household_id: str, medication_id: str
) -> HouseholdOtcMedication | None:
    assignment = db.get(MemberOtcAssignment, medication_id)
    if assignment is not None:
        otc = locked_get(db, HouseholdOtcMedication, assignment.otc_medication_id)
        if otc is not None and otc.household_id == household_id:
            return otc
        return None
    otc = locked_get(db, HouseholdOtcMedication, medication_id)
    if otc is None or otc.household_id != household_id:
        return None
    return otc


def prescription_fields(item: Medication) -> dict:
    return {
        **inventory_fields(item),
        "pharmacy": item.pharmacy,
        "rx_number": item.rx_number,
        "refills_remaining": item.refills_remaining,
    }


def consume_administered_dose(
    db: Session, household_id: str, entry_payload: dict, *, submitted: bool
) -> None:
    if not submitted or str(entry_payload.get("outcome") or "").lower() != "given":
        return
    item = stock_for_administered_id(
        db, household_id, entry_payload.get("medication_id")
    )
    if item is not None:
        consume_stock(item, _dose_quantity(entry_payload))


def _dose_quantity(payload: dict) -> float:
    try:
        return float(payload.get("quantity_given") or 1)
    except (TypeError, ValueError):
        return 1.0


def inventory_fields(item: StockRecord) -> dict:
    return {
        "quantity_on_hand": item.quantity_on_hand,
        "refill_quantity": item.refill_quantity,
        "refill_reminder_level": item.refill_reminder_level,
        "last_refill_on": (
            item.last_refill_on.isoformat() if item.last_refill_on else None
        ),
        "needs_refill": needs_refill(
            quantity_on_hand=item.quantity_on_hand,
            refill_reminder_level=item.refill_reminder_level,
        ),
    }
