from datetime import UTC, datetime

from app.api import deps
from app.core.auth.scopes import ALL_SCOPES
from app.core.auth.user import AuthUser
from app.forms.catalog import get_form_type


def _household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]


def _child(client, household_id: str) -> str:
    return client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Jordan", "last_name": "Lee"},
    ).json()["id"]


def _note(member_id: str, **extra: object) -> dict:
    payload = {
        "member_id": member_id,
        "occurred_at": datetime(2026, 8, 19, 15, 4, tzinfo=UTC).isoformat(),
        "location": "Kitchen",
        "antecedent": "Asked to do homework",
        "behavior": "Threw pencil",
        "intervention": "Cool-down in room",
        "consequence": "Lost screen time",
        "duration_minutes": 15,
        "follow_up": "Talk after dinner",
        "notified": ["Case worker"],
    }
    payload.update(extra)
    return payload


def test_behavior_form_collects_abc_fields() -> None:
    form = get_form_type("behavior")
    assert form.name == "Behavior"
    props = form.schema["properties"]
    for key in (
        "location",
        "antecedent",
        "behavior",
        "intervention",
        "consequence",
        "duration_minutes",
        "follow_up",
        "notified",
    ):
        assert key in props
    assert form.scope == "member"


def test_create_behavior_note_is_viewable_as_behavior_form(client) -> None:
    household_id = _household(client)
    member_id = _child(client, household_id)
    created = client.post(
        f"/api/households/{household_id}/discipline", json=_note(member_id)
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    log_id = created.json()["log_entry_id"]
    record = client.get(f"/api/households/{household_id}/discipline/{record_id}")
    assert record.status_code == 200, record.text
    body = record.json()
    assert body["antecedent"] == "Asked to do homework"
    assert body["behavior"] == "Threw pencil"
    assert body["intervention"] == "Cool-down in room"
    assert body["log_entry_id"] == log_id
    viewed = client.get(f"/api/households/{household_id}/logs/{log_id}")
    assert viewed.status_code == 200, viewed.text
    log = viewed.json()
    assert log["form_type_code"] == "behavior"
    assert log["form_name"] == "Behavior"
    assert log["payload"]["antecedent"] == "Asked to do homework"
    assert log["payload"]["intervention"] == "Cool-down in room"
    assert log["payload"]["consequence"] == "Lost screen time"


def test_update_behavior_note_edits_record_and_form(client) -> None:
    household_id = _household(client)
    member_id = _child(client, household_id)
    created = client.post(
        f"/api/households/{household_id}/discipline", json=_note(member_id)
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    updated = client.patch(
        f"/api/households/{household_id}/discipline/{record_id}",
        json=_note(
            member_id,
            behavior="Threw pencil and yelled",
            follow_up="Call worker tomorrow",
        ),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["behavior"] == "Threw pencil and yelled"
    assert body["follow_up"] == "Call worker tomorrow"
    log = client.get(
        f"/api/households/{household_id}/logs/{body['log_entry_id']}"
    ).json()
    assert log["form_type_code"] == "behavior"
    assert log["status"] == "submitted"
    assert log["payload"]["behavior"] == "Threw pencil and yelled"
    assert log["payload"]["follow_up"] == "Call worker tomorrow"


def test_behavior_log_created_from_logs_appears_on_behavior_tab(client) -> None:
    household_id = _household(client)
    member_id = _child(client, household_id)
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "behavior",
            "subject_member_id": member_id,
            "occurred_at": datetime(2026, 8, 19, 15, 4, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "location": "Kitchen",
                "antecedent": "Asked to do homework",
                "behavior": "Threw pencil",
                "intervention": "Cool-down in room",
                "consequence": "Lost screen time",
                "duration_minutes": 15,
                "follow_up": "Talk after dinner",
                "notified": ["Case worker"],
            },
        },
    )
    assert created.status_code == 201, created.text
    log_id = created.json()["id"]
    notes = client.get(f"/api/households/{household_id}/discipline").json()
    match = next((item for item in notes if item["log_entry_id"] == log_id), None)
    assert match is not None
    assert match["behavior"] == "Threw pencil"
    updated = client.patch(
        f"/api/households/{household_id}/discipline/{match['id']}",
        json=_note(member_id, behavior="Threw pencil and yelled"),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["behavior"] == "Threw pencil and yelled"


def test_adult_without_edit_cannot_update_behavior_note(client) -> None:
    household_id = _household(client)
    member_id = _child(client, household_id)
    created = client.post(
        f"/api/households/{household_id}/discipline", json=_note(member_id)
    )
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    helper = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "adult",
            "first_name": "Sam",
            "last_name": "Helper",
            "email": "sam@example.com",
        },
    )
    assert helper.status_code == 201, helper.text
    client.app.dependency_overrides[deps.get_current_user] = lambda: AuthUser(
        subject="sub-sam",
        email="sam@example.com",
        name="Sam Helper",
        scopes=ALL_SCOPES,
    )
    client.get("/api/me")
    client.app.dependency_overrides[deps.get_current_user] = lambda: AuthUser(
        subject="sub-ada",
        email="ada@example.com",
        name="Ada Admin",
        scopes=ALL_SCOPES,
    )
    granted = client.put(
        f"/api/households/{household_id}/members/{helper.json()['id']}/permissions",
        json={
            "grants": [
                {"resource": "tab.discipline", "action": "view"},
            ]
        },
    )
    assert granted.status_code == 200, granted.text
    client.app.dependency_overrides[deps.get_current_user] = lambda: AuthUser(
        subject="sub-sam",
        email="sam@example.com",
        name="Sam Helper",
        scopes=ALL_SCOPES,
    )
    response = client.patch(
        f"/api/households/{household_id}/discipline/{record_id}",
        json=_note(member_id, behavior="Changed without permission"),
    )
    assert response.status_code == 403
