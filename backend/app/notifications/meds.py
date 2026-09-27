from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Household,
    HouseholdMember,
    HouseholdOtcMedication,
    Medication,
    PersonProfile,
)
from app.notifications.messages import Notification
from app.notifications.preferences import HOUSEHOLD_SUBJECT
from app.notifications.topics import MED_DOSE_DUE, MED_REFILL_NEEDED
from app.services.households import legal_name
from app.services.inventory import needs_refill
from app.services.med_rules import is_administerable
from app.services.timezones import format_clock_12h, from_utc_naive, to_utc_naive, zone

MAX_LEAD = timedelta(minutes=180)
# Repeats can continue after the scheduled time. The engine decides which
# attempt is due; the collector only has to keep the dose in range.
DOSE_FOLLOWUP = timedelta(hours=12)


def collect_med_reminders(
    db: Session, household: Household, now: datetime
) -> list[Notification]:
    local_now = from_utc_naive(now, household.timezone)
    notes = _dose_reminders(db, household, now, local_now)
    notes.extend(_refill_reminders(db, household, local_now.date()))
    return notes


def _dose_reminders(
    db: Session, household: Household, now: datetime, local_now: datetime
) -> list[Notification]:
    notes: list[Notification] = []
    meds = _household_meds(db, household.id)
    for med in meds:
        if med.is_prn or med.hold_reason or not med.schedule_times:
            continue
        profile = med.profile
        for clock, scheduled_utc, scheduled_date in _due_slots(
            med.schedule_times, household.timezone, local_now, now
        ):
            if not is_administerable(
                active=med.active,
                start_date=med.start_date,
                end_date=med.end_date,
                on=scheduled_date,
            ):
                continue
            notes.append(
                Notification(
                    topic=MED_DOSE_DUE,
                    title="Medication due",
                    body=(
                        f"{legal_name(profile)}: {med.name} {med.dose} is due "
                        f"at {format_clock_12h(clock)}."
                    ),
                    household_id=household.id,
                    subject_member_id=profile.member_id,
                    dedupe_key=(
                        f"{MED_DOSE_DUE}:{med.id}:{scheduled_date.isoformat()}:{clock}"
                    ),
                    deliver_at=scheduled_utc,
                    deliver_until=scheduled_utc + DOSE_FOLLOWUP,
                    medication_id=med.id,
                )
            )
    return notes


def _due_slots(
    schedule_times: list, tz_name: str, local_now: datetime, now: datetime
) -> list[tuple[str, datetime, date]]:
    due: list[tuple[str, datetime, date]] = []
    dates = (local_now.date(), local_now.date() - timedelta(days=1))
    for raw in schedule_times:
        clock = _normalize_clock(str(raw))
        if clock is None:
            continue
        hour, minute = (int(part) for part in clock.split(":"))
        for scheduled_date in dates:
            local_scheduled = datetime.combine(
                scheduled_date,
                datetime.min.time().replace(hour=hour, minute=minute),
                tzinfo=zone(tz_name),
            )
            scheduled_utc = to_utc_naive(local_scheduled)
            if scheduled_utc - MAX_LEAD <= now < scheduled_utc + DOSE_FOLLOWUP:
                due.append((clock, scheduled_utc, scheduled_date))
    return due


def _refill_reminders(db: Session, household: Household, on) -> list[Notification]:
    notes: list[Notification] = []
    for med in _household_meds(db, household.id):
        if not med.active or (med.end_date is not None and on > med.end_date):
            continue
        if not needs_refill(
            quantity_on_hand=med.quantity_on_hand,
            refill_reminder_level=med.refill_reminder_level,
        ):
            continue
        profile = med.profile
        notes.append(
            Notification(
                topic=MED_REFILL_NEEDED,
                title="Refill needed",
                body=(
                    f"{legal_name(profile)}: {med.name} needs a refill "
                    f"({_qty(med.quantity_on_hand)} left, remind at "
                    f"{_qty(med.refill_reminder_level)})."
                ),
                household_id=household.id,
                subject_member_id=profile.member_id,
                dedupe_key=f"{MED_REFILL_NEEDED}:medication:{med.id}:{on.isoformat()}",
            )
        )
    cabinet = db.scalars(
        select(HouseholdOtcMedication).where(
            HouseholdOtcMedication.household_id == household.id,
            HouseholdOtcMedication.active.is_(True),
        )
    )
    for item in cabinet:
        if not needs_refill(
            quantity_on_hand=item.quantity_on_hand,
            refill_reminder_level=item.refill_reminder_level,
        ):
            continue
        notes.append(
            Notification(
                topic=MED_REFILL_NEEDED,
                title="Refill needed",
                body=(
                    f"Medicine cabinet: {item.name} needs a refill "
                    f"({_qty(item.quantity_on_hand)} left, remind at "
                    f"{_qty(item.refill_reminder_level)})."
                ),
                household_id=household.id,
                subject_member_id=HOUSEHOLD_SUBJECT,
                dedupe_key=f"{MED_REFILL_NEEDED}:otc:{item.id}:{on.isoformat()}",
            )
        )
    return notes


def _household_meds(db: Session, household_id: str) -> list[Medication]:
    rows = db.scalars(
        select(Medication)
        .join(Medication.profile)
        .join(PersonProfile.member)
        .where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.status == "active",
        )
        .options(joinedload(Medication.profile))
    )
    return list(rows.unique())


def _normalize_clock(value: str) -> str | None:
    parts = value.strip().split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def _qty(value: float | None) -> str:
    if value is None:
        return "0"
    if float(value).is_integer():
        return str(int(value))
    return str(value)
