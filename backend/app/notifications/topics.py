from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import DomainError

MED_DOSE_DUE = "meds.dose_due"
MED_REFILL_NEEDED = "meds.refill_needed"


@dataclass(frozen=True)
class NotificationTopic:
    code: str
    name: str
    description: str
    module: str
    applies_to: str


TOPICS: tuple[NotificationTopic, ...] = (
    NotificationTopic(
        MED_DOSE_DUE,
        "Dose reminders",
        "Remind when a scheduled medication dose is due.",
        "meds",
        "member",
    ),
    NotificationTopic(
        MED_REFILL_NEEDED,
        "Refill reminders",
        "Remind when a medication or the medicine cabinet is running low.",
        "meds",
        "any",
    ),
)

_BY_CODE = {item.code: item for item in TOPICS}


def get_topic(code: str) -> NotificationTopic:
    try:
        return _BY_CODE[code]
    except KeyError as exc:
        raise DomainError(f"Unknown notification topic: {code}") from exc


def serialize_topics() -> list[dict]:
    return [
        {
            "code": item.code,
            "name": item.name,
            "description": item.description,
            "module": item.module,
            "applies_to": item.applies_to,
        }
        for item in TOPICS
    ]
