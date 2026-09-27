from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LogEntry

ADMINISTRATION_FORM = "medication_administration"


def dose_already_logged(
    db: Session,
    *,
    household_id: str,
    subject_member_id: str,
    medication_id: str,
    scheduled: datetime,
    before_minutes: int,
    after_minutes: int,
) -> bool:
    """True when a submitted administration log falls in the recipient's window."""
    start = scheduled - timedelta(minutes=before_minutes)
    end = scheduled + timedelta(minutes=after_minutes)
    rows = db.scalars(
        select(LogEntry).where(
            LogEntry.household_id == household_id,
            LogEntry.form_type_code == ADMINISTRATION_FORM,
            LogEntry.subject_member_id == subject_member_id,
            LogEntry.status == "submitted",
            LogEntry.occurred_at >= start,
            LogEntry.occurred_at <= end,
        )
    )
    for row in rows:
        payload = row.payload or {}
        if str(payload.get("medication_id") or "") == medication_id:
            return True
    return False
