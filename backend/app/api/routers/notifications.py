from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, household_service
from app.core.auth.user import AuthUser
from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.notifications.channels import build_channels, migrate_pushover_user_key
from app.notifications.dispatch import dispatch_household, utcnow
from app.notifications.preferences import (
    PARENT_ROLES,
    can_configure,
    complete_pushover_link,
    save_settings,
    send_test_notification,
    serialize_settings,
    start_pushover_link,
)
from app.notifications.schemas import (
    NotificationSettingsIn,
    NotificationTestIn,
    PushoverCompleteIn,
    PushoverStartIn,
)
from app.services.households import HouseholdService

router = APIRouter()


@router.get("/households/{household_id}/notifications")
def read_notifications(
    household_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    member_id: str | None = Query(default=None),
) -> dict:
    actor = service.require_membership(household_id, user)
    target = service.get_member(household_id, member_id or actor.id)
    if not can_configure(actor, target):
        raise DomainError(
            "You can edit your own notifications, or a child's if you are a parent.",
            403,
        )
    return serialize_settings(db, target, actor, settings=get_settings())


@router.put("/households/{household_id}/notifications")
def update_notifications(
    household_id: str,
    data: NotificationSettingsIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    actor = service.require_membership(household_id, user)
    target = service.get_member(household_id, data.member_id)
    return save_settings(
        db,
        member=target,
        actor=actor,
        email_enabled=data.email_enabled,
        pushover_enabled=data.pushover_enabled,
        pushover_user_key=data.pushover_user_key,
        dose_lead_minutes=data.dose_lead_minutes,
        dose_window_before_minutes=data.dose_window_before_minutes,
        dose_window_after_minutes=data.dose_window_after_minutes,
        dose_repeat_count=data.dose_repeat_count,
        dose_repeat_interval_minutes=data.dose_repeat_interval_minutes,
        subscriptions=[item.model_dump() for item in data.subscriptions],
        migrate_user_key=_migrator(get_settings()),
        settings=get_settings(),
    )


@router.post("/households/{household_id}/notifications/pushover/start")
def begin_pushover_subscription(
    household_id: str,
    data: PushoverStartIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    actor = service.require_membership(household_id, user)
    target = service.get_member(household_id, data.member_id)
    return start_pushover_link(
        db,
        household_id=household_id,
        member=target,
        actor=actor,
        settings=get_settings(),
        now=utcnow(),
    )


@router.post("/households/{household_id}/notifications/pushover/complete")
def finish_pushover_subscription(
    household_id: str,
    data: PushoverCompleteIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    actor = service.require_membership(household_id, user)
    target = service.get_member(household_id, data.member_id)
    return complete_pushover_link(
        db,
        household_id=household_id,
        member=target,
        actor=actor,
        rand=data.rand,
        pushover_user_key=data.pushover_user_key,
        pushover_unsubscribed=data.pushover_unsubscribed,
        now=utcnow(),
        settings=get_settings(),
    )


@router.post("/households/{household_id}/notifications/test")
def send_test(
    household_id: str,
    data: NotificationTestIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    actor = service.require_membership(household_id, user)
    target = service.get_member(household_id, data.member_id)
    return send_test_notification(
        db, member=target, actor=actor, channels=build_channels(get_settings())
    )


@router.post("/households/{household_id}/notifications/dispatch")
def dispatch_reminders(
    household_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    actor = service.require_membership(household_id, user)
    if actor.household_role not in PARENT_ROLES:
        raise DomainError("Only a parent can send reminders right now.", 403)
    results = dispatch_household(db, household_id, build_channels(get_settings()))
    return {"deliveries": results}


def _migrator(settings):
    token = (settings.pushover_api_token or "").strip()
    subscription = _subscription_code(settings)
    if not token or not subscription:
        return None

    def migrate(user_key: str) -> str:
        return migrate_pushover_user_key(
            token=token, subscription=subscription, user_key=user_key
        )

    return migrate


def _subscription_code(settings) -> str:
    explicit = (settings.pushover_subscription_code or "").strip()
    if explicit:
        return explicit
    url = (settings.pushover_subscription_url or "").strip()
    path = url.split("?", 1)[0].rstrip("/")
    if "/subscribe/" not in path:
        return ""
    return path.rsplit("/", 1)[-1]
