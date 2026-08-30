from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

DOSE_UNITS = (
    "mg",
    "mcg",
    "g",
    "mL",
    "IU",
    "units",
    "tablet",
    "capsule",
    "drop",
    "puff",
)

_DOSE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-zµμ]+)?\s*$")


def parse_dose(value: str | None) -> tuple[str | None, str]:
    text = (value or "").strip()
    if not text:
        return None, "mg"
    match = _DOSE_RE.match(text)
    if not match:
        return None, "mg"
    return _trim(Decimal(match.group(1))), match.group(2) or "mg"


def compose_dose(amount: object, unit: str | None) -> str:
    text = str(amount or "").strip()
    if not text:
        return ""
    try:
        trimmed = _trim(Decimal(text))
    except InvalidOperation:
        trimmed = text
    suffix = (unit or "mg").strip() or "mg"
    return f"{trimmed}{suffix}"


def administered_dose(unit_dose: str | None, quantity: object | None) -> str:
    amount, unit = parse_dose(unit_dose)
    if amount is None:
        return str(unit_dose or "").strip()
    try:
        qty = Decimal(str(quantity if quantity not in (None, "") else 1))
    except InvalidOperation:
        qty = Decimal(1)
    if qty <= 0:
        qty = Decimal(1)
    return compose_dose(Decimal(amount) * qty, unit)


def _trim(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
