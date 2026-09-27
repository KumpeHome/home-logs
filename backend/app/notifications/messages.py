from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Notification:
    """A reminder any module can hand to the notification engine."""

    topic: str
    title: str
    body: str
    household_id: str
    subject_member_id: str
    dedupe_key: str
    deliver_at: datetime | None = None
    deliver_until: datetime | None = None
    medication_id: str | None = None
