from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError
from app.models import HouseholdMember, NotificationPreference, NotificationSubscription
from app.notifications.engine import NotificationEngine
from app.notifications.topics import TOPICS, get_topic
from app.services.households import audit, legal_name

PARENT_ROLES = frozenset({"admin", "adult"})
LINK_TTL = timedelta(minutes=15)
HOUSEHOLD_SUBJECT = ""


def can_configure(actor: HouseholdMember, target: HouseholdMember) -> bool:
    if actor.household_id != target.household_id or target.status != "active":
        return False
    if actor.id == target.id:
        return True
    return actor.household_role in PARENT_ROLES and target.household_role == "child"


def save_settings(
    db: Session,
    *,
    member: HouseholdMember,
    actor: HouseholdMember,
    email_enabled: bool,
    pushover_enabled: bool,
    pushover_user_key: str | None,
    dose_lead_minutes: int,
    subscriptions: list[dict],
    dose_window_before_minutes: int = 30,
    dose_window_after_minutes: int = 60,
    dose_repeat_count: int = 1,
    dose_repeat_interval_minutes: int = 15,
    migrate_user_key: Callable[[str], str] | None = None,
    settings=None,
) -> dict:
    _require_configure(actor, member)
    _validate_dose_rules(
        dose_lead_minutes,
        dose_window_before_minutes,
        dose_window_after_minutes,
        dose_repeat_count,
        dose_repeat_interval_minutes,
    )
    preference = _preference(db, member.id)
    preference.email_enabled = email_enabled
    preference.dose_lead_minutes = dose_lead_minutes
    preference.dose_window_before_minutes = dose_window_before_minutes
    preference.dose_window_after_minutes = dose_window_after_minutes
    preference.dose_repeat_count = dose_repeat_count
    preference.dose_repeat_interval_minutes = dose_repeat_interval_minutes
    _apply_pushover_key(
        preference,
        enabled=pushover_enabled,
        user_key=pushover_user_key,
        migrate_user_key=migrate_user_key,
    )
    if preference.email_enabled and not member.email:
        raise DomainError("Add an email address before turning on email reminders.")
    if preference.pushover_enabled and not preference.pushover_user_key:
        raise DomainError(
            "Subscribe with Pushover or enter a user key before turning on Pushover."
        )
    _replace_subscriptions(db, member, subscriptions)
    audit(
        db,
        household_id=member.household_id,
        actor_subject=getattr(actor, "auth_subject", None) or actor.id,
        actor_email=actor.email,
        action="update",
        entity_type="notification_preferences",
        entity_id=member.id,
        summary=f"Updated notifications for {legal_name(member.profile)}",
    )
    db.flush()
    return serialize_settings(db, member, actor, settings=settings)


def start_pushover_link(
    db: Session,
    *,
    household_id: str,
    member: HouseholdMember,
    actor: HouseholdMember,
    settings,
    now: datetime,
) -> dict:
    del household_id
    _require_configure(actor, member)
    subscription_url = (settings.pushover_subscription_url or "").strip()
    public_app_url = (settings.public_app_url or "").strip().rstrip("/")
    if not subscription_url or not public_app_url:
        raise DomainError("Pushover subscriptions are not configured.")
    token = secrets.token_urlsafe(24)
    preference = _preference(db, member.id)
    preference.pushover_link_hash = _token_hash(token)
    preference.pushover_link_expires_at = now + LINK_TTL
    db.flush()
    success = (
        f"{public_app_url}/notifications/pushover?"
        f"{urlencode({'member': member.id, 'rand': token})}"
    )
    failure = (
        f"{public_app_url}/notifications/pushover?"
        f"{urlencode({'member': member.id, 'pushover_failed': '1'})}"
    )
    joiner = "&" if "?" in subscription_url else "?"
    subscribe_url = (
        f"{subscription_url}{joiner}"
        f"{urlencode({'success': success, 'failure': failure})}"
    )
    return {"subscribe_url": subscribe_url}


def complete_pushover_link(
    db: Session,
    *,
    household_id: str,
    member: HouseholdMember,
    actor: HouseholdMember,
    rand: str,
    pushover_user_key: str | None,
    pushover_unsubscribed: bool,
    now: datetime,
    settings=None,
) -> dict:
    del household_id
    _require_configure(actor, member)
    preference = _preference(db, member.id)
    _require_link_token(preference, rand, now)
    preference.pushover_link_hash = None
    preference.pushover_link_expires_at = None
    if pushover_unsubscribed or not (pushover_user_key or "").strip():
        preference.pushover_user_key = None
        preference.pushover_key_source = None
        preference.pushover_enabled = False
    else:
        preference.pushover_user_key = pushover_user_key.strip()
        preference.pushover_key_source = "subscription"
        preference.pushover_enabled = True
    audit(
        db,
        household_id=member.household_id,
        actor_subject=getattr(actor, "auth_subject", None) or actor.id,
        actor_email=actor.email,
        action="update",
        entity_type="notification_preferences",
        entity_id=member.id,
        summary=f"Updated Pushover for {legal_name(member.profile)}",
    )
    db.flush()
    return serialize_settings(db, member, actor, settings=settings)


def send_test_notification(
    db: Session, *, member: HouseholdMember, actor: HouseholdMember, channels
) -> dict:
    _require_configure(actor, member)
    preference = db.scalars(
        select(NotificationPreference).where(
            NotificationPreference.member_id == member.id
        )
    ).first()
    if preference is None or not (
        preference.email_enabled or preference.pushover_enabled
    ):
        raise DomainError("Turn on email or Pushover and save before sending a test.")
    name = legal_name(member.profile)
    results = NotificationEngine(db, channels).deliver_to_member(
        member,
        preference,
        title="Home Logs test",
        body=f"This is a test notification for {name}.",
    )
    if not any(item["status"] == "sent" for item in results):
        raise DomainError(_test_problem(results))
    return {"deliveries": results}


def _test_problem(results: list[dict]) -> str:
    parts: list[str] = []
    for item in results:
        channel = "Email" if item["channel"] == "email" else "Pushover"
        if item["status"] == "unconfigured":
            parts.append(f"{channel} is not set up on the server yet.")
        elif item["detail"]:
            parts.append(f"{channel} could not be sent.")
        else:
            parts.append(f"{channel} was not sent.")
    return " ".join(parts) or "The test could not be sent."


def serialize_settings(
    db: Session, member: HouseholdMember, actor: HouseholdMember, settings=None
) -> dict:
    preference = db.scalars(
        select(NotificationPreference).where(
            NotificationPreference.member_id == member.id
        )
    ).first()
    rows = db.scalars(
        select(NotificationSubscription).where(
            NotificationSubscription.member_id == member.id
        )
    )
    subscription_url = ""
    if settings is not None:
        subscription_url = (settings.pushover_subscription_url or "").strip()
    return {
        "member_id": member.id,
        "member_name": legal_name(member.profile),
        "household_role": member.household_role,
        "email": member.email,
        "email_enabled": bool(preference and preference.email_enabled),
        "pushover_enabled": bool(preference and preference.pushover_enabled),
        "pushover_connected": bool(preference and preference.pushover_user_key),
        "pushover_key_source": preference.pushover_key_source if preference else None,
        "pushover_subscription_available": bool(subscription_url),
        "dose_lead_minutes": _stored(preference, "dose_lead_minutes", 15),
        "dose_window_before_minutes": _stored(
            preference, "dose_window_before_minutes", 30
        ),
        "dose_window_after_minutes": _stored(
            preference, "dose_window_after_minutes", 60
        ),
        "dose_repeat_count": _stored(preference, "dose_repeat_count", 1),
        "dose_repeat_interval_minutes": _stored(
            preference, "dose_repeat_interval_minutes", 15
        ),
        "subscriptions": [
            {
                "topic": row.topic,
                "subject_member_id": row.subject_member_id or None,
            }
            for row in rows
        ],
        "subjects": _subjects(db, member),
        "topics": [
            {
                "code": item.code,
                "name": item.name,
                "description": item.description,
                "applies_to": item.applies_to,
            }
            for item in TOPICS
        ],
        "configurable_members": [
            {
                "id": item.id,
                "name": legal_name(item.profile),
                "household_role": item.household_role,
            }
            for item in configurable_members(db, actor)
        ],
    }


def configurable_members(db: Session, actor: HouseholdMember) -> list[HouseholdMember]:
    members = [_with_profile(db, actor)]
    if actor.household_role not in PARENT_ROLES:
        return members
    children = db.scalars(
        select(HouseholdMember)
        .where(
            HouseholdMember.household_id == actor.household_id,
            HouseholdMember.household_role == "child",
            HouseholdMember.status == "active",
        )
        .options(joinedload(HouseholdMember.profile))
    )
    members.extend(child for child in children.unique() if child.id != actor.id)
    return members


def _subjects(db: Session, member: HouseholdMember) -> list[dict]:
    people = [_with_profile(db, member)]
    if member.household_role in PARENT_ROLES:
        children = db.scalars(
            select(HouseholdMember)
            .where(
                HouseholdMember.household_id == member.household_id,
                HouseholdMember.household_role == "child",
                HouseholdMember.status == "active",
            )
            .options(joinedload(HouseholdMember.profile))
        )
        people.extend(child for child in children.unique() if child.id != member.id)
    subjects = [
        {"id": person.id, "name": legal_name(person.profile), "kind": "member"}
        for person in people
    ]
    subjects.append({"id": None, "name": "Medicine cabinet", "kind": "household"})
    return subjects


def _replace_subscriptions(
    db: Session, member: HouseholdMember, subscriptions: list[dict]
) -> None:
    watchable = _watchable_ids(db, member)
    seen: set[tuple[str, str]] = set()
    cleaned: list[tuple[str, str]] = []
    for item in subscriptions:
        topic_code = item["topic"] if isinstance(item, dict) else item.topic
        raw_subject = (
            item["subject_member_id"]
            if isinstance(item, dict)
            else item.subject_member_id
        )
        topic = get_topic(topic_code)
        subject = raw_subject or HOUSEHOLD_SUBJECT
        if subject == HOUSEHOLD_SUBJECT:
            if topic.applies_to == "member":
                raise DomainError("Dose reminders have to be for a person.")
        elif subject not in watchable:
            raise DomainError(
                "Choose reminders for yourself or a child in this household."
            )
        pair = (topic.code, subject)
        if pair not in seen:
            seen.add(pair)
            cleaned.append(pair)
    db.execute(
        delete(NotificationSubscription).where(
            NotificationSubscription.member_id == member.id
        )
    )
    for topic_code, subject in cleaned:
        db.add(
            NotificationSubscription(
                member_id=member.id, topic=topic_code, subject_member_id=subject
            )
        )


def _watchable_ids(db: Session, member: HouseholdMember) -> set[str]:
    ids = {member.id}
    if member.household_role not in PARENT_ROLES:
        return ids
    children = db.scalars(
        select(HouseholdMember.id).where(
            HouseholdMember.household_id == member.household_id,
            HouseholdMember.household_role == "child",
            HouseholdMember.status == "active",
        )
    )
    ids.update(children)
    return ids


def _apply_pushover_key(
    preference: NotificationPreference,
    *,
    enabled: bool,
    user_key: str | None,
    migrate_user_key: Callable[[str], str] | None,
) -> None:
    if user_key is not None:
        cleaned = user_key.strip()
        if not cleaned:
            preference.pushover_user_key = None
            preference.pushover_key_source = None
        else:
            if len(cleaned) > 128:
                raise DomainError("That Pushover user key is too long.")
            if migrate_user_key is not None:
                preference.pushover_user_key = migrate_user_key(cleaned)
                preference.pushover_key_source = "subscription"
            else:
                preference.pushover_user_key = cleaned
                preference.pushover_key_source = "user_key"
    preference.pushover_enabled = enabled


def _validate_dose_rules(
    lead: int, before: int, after: int, count: int, interval: int
) -> None:
    if not 0 <= lead <= 180:
        raise DomainError("Dose lead time must be between 0 and 180 minutes.")
    if not 0 <= before <= 240:
        raise DomainError("Minutes before a dose must be between 0 and 240.")
    if not 0 <= after <= 240:
        raise DomainError("Minutes after a dose must be between 0 and 240.")
    if not 1 <= count <= 10:
        raise DomainError("Reminders can be sent from 1 to 10 times.")
    if count > 1 and not 1 <= interval <= 180:
        raise DomainError("Minutes between reminders must be between 1 and 180.")
    if (count - 1) * max(interval, 0) > 12 * 60:
        raise DomainError("Repeated reminders have to finish within 12 hours.")


def _stored(preference: NotificationPreference | None, name: str, default: int) -> int:
    if preference is None:
        return default
    value = getattr(preference, name)
    return default if value is None else int(value)


def _require_configure(actor: HouseholdMember, target: HouseholdMember) -> None:
    if not can_configure(actor, target):
        raise DomainError(
            "You can edit your own notifications, or a child's if you are a parent.",
            403,
        )


def _require_link_token(
    preference: NotificationPreference, rand: str, now: datetime
) -> None:
    expires = preference.pushover_link_expires_at
    expected = preference.pushover_link_hash
    if (
        not rand
        or not expected
        or expires is None
        or now > expires
        or not hmac.compare_digest(expected, _token_hash(rand))
    ):
        raise DomainError(
            "That Pushover link is invalid or expired. Start the subscription again."
        )


def _preference(db: Session, member_id: str) -> NotificationPreference:
    row = db.scalars(
        select(NotificationPreference).where(
            NotificationPreference.member_id == member_id
        )
    ).first()
    if row is None:
        row = NotificationPreference(member_id=member_id)
        db.add(row)
        db.flush()
    return row


def _with_profile(db: Session, member: HouseholdMember) -> HouseholdMember:
    if member.profile is not None:
        return member
    loaded = db.scalars(
        select(HouseholdMember)
        .where(HouseholdMember.id == member.id)
        .options(joinedload(HouseholdMember.profile))
    ).first()
    return loaded or member


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
