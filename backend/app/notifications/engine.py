from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    HouseholdMember,
    NotificationDelivery,
    NotificationPreference,
    NotificationSubscription,
)
from app.notifications.administration import dose_already_logged
from app.notifications.channels import DeliveryChannel
from app.notifications.messages import Notification
from app.notifications.topics import get_topic

ATTEMPT_GRACE = timedelta(minutes=15)
logger = logging.getLogger(__name__)


class NotificationEngine:
    """Delivers a notification to every subscribed member on their enabled channels."""

    def __init__(self, db: Session, channels: dict[str, DeliveryChannel]) -> None:
        self.db = db
        self.channels = channels

    def publish(self, notification: Notification, now: datetime) -> list[dict]:
        get_topic(notification.topic)
        subscriptions = self.db.scalars(
            select(NotificationSubscription).where(
                NotificationSubscription.topic == notification.topic,
                NotificationSubscription.subject_member_id
                == notification.subject_member_id,
            )
        )
        results: list[dict] = []
        for subscription in subscriptions:
            member = self.db.get(HouseholdMember, subscription.member_id)
            if (
                member is None
                or member.household_id != notification.household_id
                or member.status != "active"
            ):
                continue
            preference = self.db.scalars(
                select(NotificationPreference).where(
                    NotificationPreference.member_id == member.id
                )
            ).first()
            if preference is None:
                continue
            prepared = self._for_delivery(preference, notification, now)
            if prepared is None:
                continue
            results.extend(self._enabled_channels(member, preference, prepared))
        return results

    def deliver_to_member(
        self,
        member: HouseholdMember,
        preference: NotificationPreference,
        *,
        title: str,
        body: str,
    ) -> list[dict]:
        """Send once to a member's enabled channels, without reminder dedupe."""
        notification = Notification(
            topic="system.test",
            title=title,
            body=body,
            household_id=member.household_id,
            subject_member_id=member.id,
            dedupe_key="system.test",
        )
        return self._enabled_channels(member, preference, notification, record=False)

    def _enabled_channels(
        self,
        member: HouseholdMember,
        preference: NotificationPreference,
        notification: Notification,
        *,
        record: bool = True,
    ) -> list[dict]:
        results: list[dict] = []
        if preference.email_enabled:
            results.append(
                self._deliver(
                    member,
                    "email",
                    member.email,
                    notification,
                    missing="no email address",
                    record=record,
                )
            )
        if preference.pushover_enabled:
            results.append(
                self._deliver(
                    member,
                    "pushover",
                    preference.pushover_user_key,
                    notification,
                    missing="no Pushover key",
                    record=record,
                )
            )
        return results

    def _deliver(
        self,
        member: HouseholdMember,
        channel_code: str,
        destination: str | None,
        notification: Notification,
        *,
        missing: str,
        record: bool = True,
    ) -> dict:
        base = {
            "member_id": member.id,
            "channel": channel_code,
            "dedupe_key": notification.dedupe_key,
        }
        if not destination:
            return {**base, "status": "skipped", "detail": missing}
        channel = self.channels.get(channel_code)
        if channel is None:
            return {**base, "status": "unconfigured", "detail": None}
        if not record:
            try:
                channel.deliver(
                    destination=destination,
                    title=notification.title,
                    body=notification.body,
                )
            except Exception:
                logger.exception("Notification delivery failed")
                return {**base, "status": "failed", "detail": None}
            return {**base, "status": "sent", "detail": None}
        if not self._reserve(member, channel_code, notification):
            return {**base, "status": "skipped", "detail": "already sent"}
        try:
            channel.deliver(
                destination=destination,
                title=notification.title,
                body=notification.body,
            )
        except Exception:
            self._release(member, channel_code, notification)
            logger.exception("Notification delivery failed")
            return {**base, "status": "failed", "detail": None}
        return {**base, "status": "sent", "detail": None}

    def _reserve(
        self,
        member: HouseholdMember,
        channel_code: str,
        notification: Notification,
    ) -> bool:
        """Insert the delivery row before sending so a second poller cannot send too."""
        try:
            with self.db.begin_nested():
                self.db.add(
                    NotificationDelivery(
                        recipient_member_id=member.id,
                        channel=channel_code,
                        dedupe_key=notification.dedupe_key,
                        topic=notification.topic,
                    )
                )
                self.db.flush()
        except IntegrityError:
            return False
        return True

    def _release(
        self,
        member: HouseholdMember,
        channel_code: str,
        notification: Notification,
    ) -> None:
        self.db.execute(
            delete(NotificationDelivery).where(
                NotificationDelivery.recipient_member_id == member.id,
                NotificationDelivery.channel == channel_code,
                NotificationDelivery.dedupe_key == notification.dedupe_key,
            )
        )
        self.db.flush()

    def _for_delivery(
        self,
        preference: NotificationPreference,
        notification: Notification,
        now: datetime,
    ) -> Notification | None:
        if notification.deliver_until is not None and now >= notification.deliver_until:
            return None
        if notification.deliver_at is None:
            return notification
        if notification.medication_id and _already_logged(
            self.db, preference, notification
        ):
            return None
        attempt = _due_attempt(preference, notification.deliver_at, now)
        if attempt is None:
            return None
        count = _pref_int(preference.dose_repeat_count, 1)
        body = notification.body
        if count > 1:
            body = f"{body} Reminder {attempt + 1} of {count}."
        return replace(
            notification,
            body=body,
            dedupe_key=f"{notification.dedupe_key}:{attempt}",
        )


def _already_logged(
    db: Session, preference: NotificationPreference, notification: Notification
) -> bool:
    scheduled = notification.deliver_at
    medication_id = notification.medication_id
    if scheduled is None or not medication_id:
        return False
    return dose_already_logged(
        db,
        household_id=notification.household_id,
        subject_member_id=notification.subject_member_id,
        medication_id=medication_id,
        scheduled=scheduled,
        before_minutes=_pref_int(preference.dose_window_before_minutes, 30),
        after_minutes=_pref_int(preference.dose_window_after_minutes, 60),
    )


def _due_attempt(
    preference: NotificationPreference, scheduled: datetime, now: datetime
) -> int | None:
    count = max(_pref_int(preference.dose_repeat_count, 1), 1)
    interval = _pref_int(preference.dose_repeat_interval_minutes, 15)
    lead = _pref_int(preference.dose_lead_minutes, 15)
    first = scheduled - timedelta(minutes=lead)
    for attempt in range(count):
        due = first + timedelta(minutes=attempt * interval if count > 1 else 0)
        if attempt + 1 < count:
            closes = due + timedelta(minutes=max(interval, 1))
        else:
            closes = max(due + ATTEMPT_GRACE, scheduled + ATTEMPT_GRACE)
        if due <= now < closes:
            return attempt
    return None


def _pref_int(value: int | None, default: int) -> int:
    return default if value is None else int(value)
