from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from app.api import deps
from app.core.auth.scopes import ALL_SCOPES
from app.core.auth.user import AuthUser
from app.core.config import get_settings
from app.models import (
    Household,
    HouseholdMember,
    HouseholdOtcMedication,
    LogEntry,
    Medication,
    NotificationDelivery,
    PersonProfile,
)
from app.notifications.dispatch import dispatch_household
from app.notifications.engine import NotificationEngine
from app.notifications.messages import Notification
from app.notifications.preferences import (
    complete_pushover_link,
    save_settings,
    start_pushover_link,
)
from app.notifications.topics import MED_DOSE_DUE, MED_REFILL_NEEDED


@pytest.fixture(autouse=True)
def _restore_notification_settings():
    settings = get_settings()
    previous = (
        settings.pushover_subscription_url,
        settings.public_app_url,
        settings.pushover_api_token,
        settings.pushover_subscription_code,
    )
    yield
    (
        settings.pushover_subscription_url,
        settings.public_app_url,
        settings.pushover_api_token,
        settings.pushover_subscription_code,
    ) = previous


def _household(db, timezone: str = "America/Chicago") -> Household:
    household = Household(name="Home", household_type="family", timezone=timezone)
    db.add(household)
    db.flush()
    return household


def _member(
    db,
    household: Household,
    role: str,
    first: str,
    last: str,
    email: str | None = None,
) -> HouseholdMember:
    member = HouseholdMember(
        household_id=household.id,
        household_role=role,
        status="active",
        email=email,
    )
    db.add(member)
    db.flush()
    profile = PersonProfile(member_id=member.id, first_name=first, last_name=last)
    db.add(profile)
    member.profile = profile
    db.flush()
    return member


class RecordingChannel:
    def __init__(self, code: str) -> None:
        self.code = code
        self.sent: list[tuple[str, str, str]] = []

    def deliver(self, *, destination: str, title: str, body: str) -> None:
        self.sent.append((destination, title, body))


def _channels() -> dict[str, RecordingChannel]:
    return {
        "email": RecordingChannel("email"),
        "pushover": RecordingChannel("pushover"),
    }


def _subscribe(db, member: HouseholdMember, **overrides) -> None:
    payload = {
        "email_enabled": True,
        "pushover_enabled": True,
        "pushover_user_key": f"user-{member.id[:8]}",
        "dose_lead_minutes": 15,
        "subscriptions": [
            {"topic": MED_DOSE_DUE, "subject_member_id": member.id},
            {"topic": MED_REFILL_NEEDED, "subject_member_id": member.id},
        ],
    }
    payload.update(overrides)
    save_settings(db, member=member, actor=member, **payload)


def test_engine_sends_email_and_pushover_when_both_are_enabled(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent)
    channels = _channels()
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Ada: Amoxicillin is due at 8:00 AM.",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-1",
    )

    results = NotificationEngine(db, channels).publish(note, _at(12, 50))

    assert {item["channel"] for item in results if item["status"] == "sent"} == {
        "email",
        "pushover",
    }
    assert channels["email"].sent[0][0] == "ada@example.com"
    assert channels["pushover"].sent[0][0] == f"user-{parent.id[:8]}"
    assert "Amoxicillin" in channels["email"].sent[0][2]


def test_engine_sends_only_the_enabled_channel(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent, pushover_enabled=False, pushover_user_key=None)
    channels = _channels()
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-email",
    )

    NotificationEngine(db, channels).publish(note, _at(12, 50))

    assert len(channels["email"].sent) == 1
    assert channels["pushover"].sent == []


def test_engine_skips_members_who_are_not_subscribed(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    channels = _channels()
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-none",
    )

    results = NotificationEngine(db, channels).publish(note, _at(12, 50))

    assert results == []
    assert channels["email"].sent == []


def test_engine_does_not_resend_the_same_reminder(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent, pushover_enabled=False, pushover_user_key=None)
    channels = _channels()
    engine = NotificationEngine(db, channels)
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-once",
    )

    engine.publish(note, _at(12, 50))
    second = engine.publish(note, _at(12, 51))

    assert len(channels["email"].sent) == 1
    assert second[0]["status"] == "skipped"


def test_reminder_is_reserved_before_it_is_sent(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent, pushover_enabled=False, pushover_user_key=None)
    seen: dict[str, bool] = {}

    class Spy:
        code = "email"

        def deliver(self, *, destination: str, title: str, body: str) -> None:
            seen["reserved"] = (
                db.scalars(select(NotificationDelivery)).first() is not None
            )

    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-claim",
    )
    NotificationEngine(db, {"email": Spy()}).publish(note, _at(12, 50))

    assert seen["reserved"] is True


def test_failed_delivery_hides_the_error_and_can_be_retried(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent, pushover_enabled=False, pushover_user_key=None)

    class Boom:
        code = "email"

        def deliver(self, *, destination: str, title: str, body: str) -> None:
            raise RuntimeError("smtp password leaked")

    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-retry",
    )
    failed = NotificationEngine(db, {"email": Boom()}).publish(note, _at(12, 50))

    assert failed[0]["status"] == "failed"
    assert failed[0]["detail"] is None
    assert "password" not in str(failed)
    assert db.scalars(select(NotificationDelivery)).first() is None

    channels = _channels()
    retried = NotificationEngine(db, channels).publish(note, _at(12, 51))

    assert retried[0]["status"] == "sent"
    assert len(channels["email"].sent) == 1


def test_engine_stops_when_deliver_until_has_passed(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(db, parent, pushover_enabled=False, pushover_user_key=None)
    channels = _channels()
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="dose-until",
        deliver_at=_at(13, 0),
        deliver_until=_at(12, 40),
    )

    results = NotificationEngine(db, channels).publish(note, _at(12, 50))

    assert results == []
    assert channels["email"].sent == []


def test_dose_reminder_respects_each_persons_lead_time(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    early = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    late = _member(db, household, "adult", "Sam", "Helper", "sam@example.com")
    _subscribe(
        db,
        early,
        dose_lead_minutes=15,
        subscriptions=[{"topic": MED_DOSE_DUE, "subject_member_id": child.id}],
    )
    _subscribe(
        db,
        late,
        dose_lead_minutes=0,
        pushover_enabled=False,
        pushover_user_key=None,
        subscriptions=[{"topic": MED_DOSE_DUE, "subject_member_id": child.id}],
    )
    med = Medication(
        profile_id=child.profile.id,
        name="Amoxicillin",
        dose="400mg",
        route="oral",
        frequency="daily",
        schedule_times=["08:00"],
        active=True,
    )
    db.add(med)
    db.flush()
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))

    assert [item[0] for item in channels["email"].sent] == ["ada@example.com"]
    assert "Amoxicillin" in channels["email"].sent[0][2]


def test_prn_and_inactive_medications_do_not_raise_dose_reminders(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(db, child)
    db.add(
        Medication(
            profile_id=child.profile.id,
            name="Ibuprofen",
            dose="200mg",
            route="oral",
            frequency="as needed",
            schedule_times=["08:00"],
            is_prn=True,
            active=True,
        )
    )
    db.add(
        Medication(
            profile_id=child.profile.id,
            name="Old Med",
            dose="1 tab",
            route="oral",
            frequency="daily",
            schedule_times=["08:00"],
            active=False,
        )
    )
    db.flush()
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(13, 0))

    assert channels["email"].sent == []


def test_parent_is_notified_for_one_child_and_not_the_other(db) -> None:
    household = _household(db)
    casey = _member(db, household, "child", "Casey", "One", "casey@example.com")
    sam = _member(db, household, "child", "Sam", "Two", "samkid@example.com")
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(
        db,
        parent,
        subscriptions=[
            {"topic": MED_DOSE_DUE, "subject_member_id": casey.id},
            {"topic": MED_REFILL_NEEDED, "subject_member_id": casey.id},
        ],
    )
    for child, name in ((casey, "Amoxicillin"), (sam, "Ibuprofen")):
        db.add(
            Medication(
                profile_id=child.profile.id,
                name=name,
                dose="200mg",
                route="oral",
                frequency="daily",
                schedule_times=["08:00"],
                active=True,
                quantity_on_hand=2,
                refill_reminder_level=10,
            )
        )
    db.flush()
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))

    bodies = [item[2] for item in channels["email"].sent]
    assert any("Casey" in body and "Amoxicillin" in body for body in bodies)
    assert not any("Sam" in body or "Ibuprofen" in body for body in bodies)


def test_dose_reminder_is_skipped_when_the_dose_was_given_in_the_window(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(
        db,
        child,
        dose_window_before_minutes=30,
        dose_window_after_minutes=60,
    )
    med = _scheduled_med(db, child, "Amoxicillin")
    _given(db, household, child, med.id, _at(12, 40))
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))

    assert channels["email"].sent == []


def test_dose_given_outside_the_window_still_reminds(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(db, child, dose_window_before_minutes=20, dose_window_after_minutes=20)
    med = _scheduled_med(db, child, "Amoxicillin")
    _given(db, household, child, med.id, _at(12, 0))
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))

    assert channels["email"].sent
    assert "Amoxicillin" in channels["email"].sent[0][2]


@pytest.mark.parametrize("outcome", ["given", "refused", "missed", "held"])
def test_any_logged_outcome_stops_the_dose_reminder(db, outcome: str) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(db, child)
    med = _scheduled_med(db, child, "Amoxicillin")
    _given(db, household, child, med.id, _at(12, 50), outcome=outcome)
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))

    assert channels["email"].sent == []


def test_missed_dose_is_reminded_again_until_the_repeat_limit(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(
        db,
        child,
        dose_lead_minutes=15,
        dose_repeat_count=2,
        dose_repeat_interval_minutes=10,
    )
    _scheduled_med(db, child, "Amoxicillin")
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))
    dispatch_household(db, household.id, channels, now=_at(12, 56))
    dispatch_household(db, household.id, channels, now=_at(13, 20))

    bodies = [item[2] for item in channels["email"].sent]
    assert len(bodies) == 2
    assert "Reminder 1 of 2" in bodies[0]
    assert "Reminder 2 of 2" in bodies[1]


def test_late_dose_is_still_reminded_after_local_midnight(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(db, child)
    _scheduled_med(db, child, "Amoxicillin", times=["23:50"])
    channels = _channels()

    dispatch_household(db, household.id, channels, now=datetime(2026, 9, 27, 5, 2))

    assert channels["email"].sent
    assert "11:50 PM" in channels["email"].sent[0][2]


def test_giving_the_dose_after_the_first_reminder_stops_repeats(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    _subscribe(
        db,
        child,
        dose_lead_minutes=15,
        dose_repeat_count=3,
        dose_repeat_interval_minutes=10,
        dose_window_before_minutes=30,
        dose_window_after_minutes=60,
    )
    med = _scheduled_med(db, child, "Amoxicillin")
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(12, 50))
    _given(db, household, child, med.id, _at(12, 52))
    dispatch_household(db, household.id, channels, now=_at(13, 5))

    assert len(channels["email"].sent) == 1


def _scheduled_med(db, member, name: str, times: list[str] | None = None) -> Medication:
    med = Medication(
        profile_id=member.profile.id,
        name=name,
        dose="400mg",
        route="oral",
        frequency="daily",
        schedule_times=times or ["08:00"],
        active=True,
    )
    db.add(med)
    db.flush()
    return med


def _given(
    db, household, member, medication_id: str, when, outcome: str = "given"
) -> None:
    db.add(
        LogEntry(
            household_id=household.id,
            form_type_code="medication_administration",
            subject_member_id=member.id,
            occurred_at=when,
            status="submitted",
            payload={
                "medication_id": medication_id,
                "medication_name": "Amoxicillin",
                "outcome": outcome,
                "quantity_given": 1,
            },
        )
    )
    db.flush()


def test_refill_reminder_includes_prescriptions_and_the_medicine_cabinet(db) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child", "casey@example.com")
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    _subscribe(
        db,
        parent,
        subscriptions=[
            {"topic": MED_REFILL_NEEDED, "subject_member_id": child.id},
            {"topic": MED_REFILL_NEEDED, "subject_member_id": None},
        ],
    )
    db.add(
        Medication(
            profile_id=child.profile.id,
            name="Amoxicillin",
            dose="400mg",
            route="oral",
            frequency="daily",
            schedule_times=[],
            active=True,
            quantity_on_hand=4,
            refill_reminder_level=10,
        )
    )
    db.add(
        HouseholdOtcMedication(
            household_id=household.id,
            name="Acetaminophen",
            dose="325mg",
            route="oral",
            active=True,
            quantity_on_hand=2,
            refill_reminder_level=8,
        )
    )
    db.flush()
    channels = _channels()

    dispatch_household(db, household.id, channels, now=_at(15, 0))

    bodies = [item[2] for item in channels["email"].sent]
    assert any("Amoxicillin" in body for body in bodies)
    assert any("Acetaminophen" in body for body in bodies)
    assert all(item[0] == "ada@example.com" for item in channels["email"].sent)


def test_manual_pushover_user_key_is_kept_when_subscriptions_are_not_configured(
    db,
) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")

    saved = save_settings(
        db,
        member=parent,
        actor=parent,
        email_enabled=False,
        pushover_enabled=True,
        pushover_user_key="uManualKey123",
        dose_lead_minutes=10,
        subscriptions=[],
    )

    assert saved["pushover_connected"] is True
    assert saved["pushover_key_source"] == "user_key"
    assert "pushover_user_key" not in saved or saved.get("pushover_user_key") in (
        None,
        "",
    )


def test_manual_pushover_user_key_is_migrated_to_a_subscription_key(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")

    def migrate(user_key: str) -> str:
        assert user_key == "uManualKey123"
        return "sSubscribedKey456"

    saved = save_settings(
        db,
        member=parent,
        actor=parent,
        email_enabled=False,
        pushover_enabled=True,
        pushover_user_key="uManualKey123",
        dose_lead_minutes=10,
        subscriptions=[],
        migrate_user_key=migrate,
    )

    assert saved["pushover_key_source"] == "subscription"
    channels = _channels()
    _subscribe_topic(db, parent, MED_DOSE_DUE, parent.id)
    note = Notification(
        topic=MED_DOSE_DUE,
        title="Medication due",
        body="Due",
        household_id=household.id,
        subject_member_id=parent.id,
        dedupe_key="migrated",
    )
    NotificationEngine(db, channels).publish(note, _at(12, 50))
    assert channels["pushover"].sent[0][0] == "sSubscribedKey456"


def test_pushover_subscription_return_stores_the_key_and_rejects_a_bad_token(
    db,
) -> None:
    household = _household(db)
    child = _member(db, household, "child", "Casey", "Child")
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    settings = get_settings()
    settings.pushover_subscription_url = "https://pushover.net/subscribe/HomeLogs-abc"
    settings.public_app_url = "http://localhost:4200"

    started = start_pushover_link(
        db,
        household_id=household.id,
        member=child,
        actor=parent,
        settings=settings,
        now=_at(12, 0),
    )
    parsed = urlparse(started["subscribe_url"])
    query = parse_qs(parsed.query)
    success = urlparse(query["success"][0])
    success_query = parse_qs(success.query)
    rand = success_query["rand"][0]
    assert parsed.netloc == "pushover.net"
    assert success_query["member"] == [child.id]
    assert success.hostname == "localhost"

    saved = complete_pushover_link(
        db,
        household_id=household.id,
        member=child,
        actor=parent,
        rand=rand,
        pushover_user_key="sFromPushover",
        pushover_unsubscribed=False,
        now=_at(12, 5),
    )
    assert saved["pushover_connected"] is True
    assert saved["pushover_key_source"] == "subscription"

    try:
        complete_pushover_link(
            db,
            household_id=household.id,
            member=child,
            actor=parent,
            rand="not-the-token",
            pushover_user_key="sAttacker",
            pushover_unsubscribed=False,
            now=_at(12, 6),
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("bad subscription token was accepted")


def test_pushover_unsubscribe_clears_the_stored_key(db) -> None:
    household = _household(db)
    parent = _member(db, household, "admin", "Ada", "Admin", "ada@example.com")
    settings = get_settings()
    settings.pushover_subscription_url = "https://pushover.net/subscribe/HomeLogs-abc"
    settings.public_app_url = "http://localhost:4200"
    started = start_pushover_link(
        db,
        household_id=household.id,
        member=parent,
        actor=parent,
        settings=settings,
        now=_at(12, 0),
    )
    rand = parse_qs(
        urlparse(parse_qs(urlparse(started["subscribe_url"]).query)["success"][0]).query
    )["rand"][0]
    complete_pushover_link(
        db,
        household_id=household.id,
        member=parent,
        actor=parent,
        rand=rand,
        pushover_user_key="sFromPushover",
        pushover_unsubscribed=False,
        now=_at(12, 1),
    )
    started_again = start_pushover_link(
        db,
        household_id=household.id,
        member=parent,
        actor=parent,
        settings=settings,
        now=_at(12, 2),
    )
    rand_again = parse_qs(
        urlparse(
            parse_qs(urlparse(started_again["subscribe_url"]).query)["success"][0]
        ).query
    )["rand"][0]

    saved = complete_pushover_link(
        db,
        household_id=household.id,
        member=parent,
        actor=parent,
        rand=rand_again,
        pushover_user_key="",
        pushover_unsubscribed=True,
        now=_at(12, 3),
    )

    assert saved["pushover_connected"] is False
    assert saved["pushover_enabled"] is False


def _subscribe_topic(db, member, topic: str, subject_member_id: str | None) -> None:
    from sqlalchemy import select

    from app.models import NotificationPreference

    pref = db.scalars(
        select(NotificationPreference).where(
            NotificationPreference.member_id == member.id
        )
    ).one()
    save_settings(
        db,
        member=member,
        actor=member,
        email_enabled=pref.email_enabled,
        pushover_enabled=pref.pushover_enabled,
        pushover_user_key=None,
        dose_lead_minutes=pref.dose_lead_minutes,
        subscriptions=[{"topic": topic, "subject_member_id": subject_member_id}],
    )


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 26, hour, minute, tzinfo=UTC).replace(tzinfo=None)


def _api_household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]


def _as(client, subject: str, email: str) -> None:
    client.app.dependency_overrides[deps.get_current_user] = lambda: AuthUser(
        subject=subject,
        email=email,
        name=email.split("@")[0].title(),
        scopes=ALL_SCOPES,
    )


def test_member_can_save_own_reminders_and_parent_can_save_a_childs(client) -> None:
    household_id = _api_household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "child",
            "first_name": "Casey",
            "last_name": "Child",
            "email": "casey@example.com",
        },
    ).json()["id"]

    own = client.put(
        f"/api/households/{household_id}/notifications",
        json={
            "member_id": _me_id(client, household_id),
            "email_enabled": True,
            "pushover_enabled": False,
            "dose_lead_minutes": 20,
            "subscriptions": [
                {"topic": MED_DOSE_DUE, "subject_member_id": child_id},
                {"topic": MED_REFILL_NEEDED, "subject_member_id": None},
            ],
        },
    )
    assert own.status_code == 200, own.text
    assert own.json()["email_enabled"] is True
    assert own.json()["dose_lead_minutes"] == 20

    child = client.put(
        f"/api/households/{household_id}/notifications",
        json={
            "member_id": child_id,
            "email_enabled": True,
            "pushover_enabled": False,
            "dose_lead_minutes": 5,
            "subscriptions": [
                {"topic": MED_DOSE_DUE, "subject_member_id": child_id},
            ],
        },
    )
    assert child.status_code == 200, child.text
    assert child.json()["member_id"] == child_id


def test_child_cannot_configure_a_parent_or_another_child(client) -> None:
    household_id = _api_household(client)
    parent_id = _me_id(client, household_id)
    casey_id = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "child",
            "first_name": "Casey",
            "last_name": "Child",
            "email": "casey@example.com",
        },
    ).json()["id"]
    sam_id = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "child",
            "first_name": "Sam",
            "last_name": "Kid",
            "email": "samkid@example.com",
        },
    ).json()["id"]
    _as(client, "sub-casey", "casey@example.com")

    parent_settings = client.put(
        f"/api/households/{household_id}/notifications",
        json=_bare(parent_id),
    )
    sibling_settings = client.put(
        f"/api/households/{household_id}/notifications",
        json=_bare(sam_id),
    )
    own = client.put(
        f"/api/households/{household_id}/notifications",
        json={
            **_bare(casey_id),
            "subscriptions": [
                {"topic": MED_DOSE_DUE, "subject_member_id": sam_id},
            ],
        },
    )

    assert parent_settings.status_code == 403
    assert sibling_settings.status_code == 403
    assert own.status_code == 400


def test_adult_cannot_configure_another_adult(client) -> None:
    household_id = _api_household(client)
    parent_id = _me_id(client, household_id)
    client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "adult",
            "first_name": "Sam",
            "last_name": "Helper",
            "email": "sam@example.com",
        },
    )
    _as(client, "sub-sam", "sam@example.com")
    client.get("/api/me")
    denied = client.put(
        f"/api/households/{household_id}/notifications",
        json=_bare(parent_id),
    )
    assert denied.status_code == 403


def test_dispatch_sends_a_due_dose_to_subscribers(client, monkeypatch) -> None:
    household_id = _api_household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    parent_id = _me_id(client, household_id)
    client.put(
        f"/api/households/{household_id}/notifications",
        json={
            "member_id": parent_id,
            "email_enabled": True,
            "pushover_enabled": True,
            "pushover_user_key": "uParentKey",
            "dose_lead_minutes": 15,
            "subscriptions": [
                {"topic": MED_DOSE_DUE, "subject_member_id": child_id},
            ],
        },
    )
    created = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Amoxicillin",
            "dose": "400mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
            "active": True,
        },
    )
    assert created.status_code == 200, created.text
    email = RecordingChannel("email")
    pushover = RecordingChannel("pushover")
    monkeypatch.setattr(
        "app.api.routers.notifications.build_channels",
        lambda _settings: {"email": email, "pushover": pushover},
    )
    monkeypatch.setattr(
        "app.notifications.dispatch.utcnow",
        lambda: _at(12, 50),
    )

    response = client.post(f"/api/households/{household_id}/notifications/dispatch")

    assert response.status_code == 200, response.text
    assert email.sent
    assert pushover.sent[0][0] == "uParentKey"
    assert "Amoxicillin" in email.sent[0][2]


def test_saved_channels_can_send_a_test_notification(client, monkeypatch) -> None:
    household_id = _api_household(client)
    parent_id = _me_id(client, household_id)
    saved = client.put(
        f"/api/households/{household_id}/notifications",
        json={
            **_bare(parent_id),
            "email_enabled": True,
            "pushover_enabled": True,
            "pushover_user_key": "uParentKey",
        },
    )
    assert saved.status_code == 200, saved.text
    email = RecordingChannel("email")
    pushover = RecordingChannel("pushover")
    monkeypatch.setattr(
        "app.api.routers.notifications.build_channels",
        lambda _settings: {"email": email, "pushover": pushover},
    )

    response = client.post(
        f"/api/households/{household_id}/notifications/test",
        json={"member_id": parent_id},
    )

    assert response.status_code == 200, response.text
    assert {item[0] for item in email.sent} == {"ada@example.com"}
    assert pushover.sent[0][0] == "uParentKey"
    assert "test" in email.sent[0][1].lower()
    again = client.post(
        f"/api/households/{household_id}/notifications/test",
        json={"member_id": parent_id},
    )
    assert again.status_code == 200, again.text
    assert len(email.sent) == 2


def test_test_notification_requires_a_saved_channel(client) -> None:
    household_id = _api_household(client)
    parent_id = _me_id(client, household_id)
    response = client.post(
        f"/api/households/{household_id}/notifications/test",
        json={"member_id": parent_id},
    )
    assert response.status_code == 400


def test_child_cannot_send_a_test_for_a_parent(client) -> None:
    household_id = _api_household(client)
    parent_id = _me_id(client, household_id)
    client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "child",
            "first_name": "Casey",
            "last_name": "Child",
            "email": "casey@example.com",
        },
    )
    _as(client, "sub-casey", "casey@example.com")
    response = client.post(
        f"/api/households/{household_id}/notifications/test",
        json={"member_id": parent_id},
    )
    assert response.status_code == 403


def _me_id(client, household_id: str) -> str:
    me = client.get("/api/me").json()
    return next(
        item["member_id"] for item in me["households"] if item["id"] == household_id
    )


def _bare(member_id: str) -> dict:
    return {
        "member_id": member_id,
        "email_enabled": False,
        "pushover_enabled": False,
        "dose_lead_minutes": 15,
        "subscriptions": [],
    }
