from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class LinkableMember(Protocol):
    email: str | None
    login_status: str
    auth_subject: str | None
    first_login_at: datetime | None


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    stripped = email.strip().lower()
    return stripped or None


def link_first_login(
    member: Any,
    *,
    subject: str,
    email: str | None,
    now: datetime,
) -> Any:
    if member.login_status != "pending":
        return member
    if normalize_email(member.email) != normalize_email(email):
        return member
    member.login_status = "linked"
    member.auth_subject = subject
    member.first_login_at = now
    return member
