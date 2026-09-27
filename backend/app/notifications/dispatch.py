from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import Household
from app.notifications.channels import DeliveryChannel
from app.notifications.engine import NotificationEngine
from app.notifications.meds import collect_med_reminders


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def dispatch_household(
    db: Session,
    household_id: str,
    channels: dict[str, DeliveryChannel],
    now: datetime | None = None,
) -> list[dict]:
    household = db.get(Household, household_id)
    if household is None:
        raise DomainError("Household not found", 404)
    moment = utcnow() if now is None else now
    engine = NotificationEngine(db, channels)
    results: list[dict] = []
    for note in collect_med_reminders(db, household, moment):
        results.extend(engine.publish(note, moment))
    return results


def dispatch_all(
    db: Session,
    channels: dict[str, DeliveryChannel],
    now: datetime | None = None,
) -> list[dict]:
    moment = utcnow() if now is None else now
    results: list[dict] = []
    for household_id in db.scalars(select(Household.id)):
        results.extend(dispatch_household(db, household_id, channels, now=moment))
    return results
