from __future__ import annotations

from datetime import date

ALLOWED_MED_FLAGS: frozenset[str] = frozenset(
    {
        "drowsy",
        "take_with_food",
        "empty_stomach",
        "avoid_alcohol",
        "dizziness",
        "photosensitivity",
        "refrigerate",
        "shake_well",
        "do_not_crush",
        "with_water",
    }
)

MED_FLAG_LABELS: dict[str, str] = {
    "drowsy": "Drowsy",
    "take_with_food": "Take with food",
    "empty_stomach": "Empty stomach",
    "avoid_alcohol": "Avoid alcohol",
    "dizziness": "May cause dizziness",
    "photosensitivity": "Photosensitivity",
    "refrigerate": "Refrigerate",
    "shake_well": "Shake well",
    "do_not_crush": "Do not crush",
    "with_water": "Take with water",
}


def normalize_med_flags(flags: list[str] | None) -> list[str]:
    values = [item for item in dict.fromkeys(flags or []) if item]
    unknown = [item for item in values if item not in ALLOWED_MED_FLAGS]
    if unknown:
        raise ValueError(f"Unknown medication flags: {', '.join(unknown)}")
    return values


def is_administerable(
    *,
    active: bool,
    start_date: date | None,
    end_date: date | None,
    on: date,
) -> bool:
    if not active:
        return False
    started = start_date is None or on >= start_date
    not_ended = end_date is None or on <= end_date
    return started and not_ended
