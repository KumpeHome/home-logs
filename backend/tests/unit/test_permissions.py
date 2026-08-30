from datetime import UTC, datetime

from app.api import deps
from app.core.auth.scopes import ALL_SCOPES
from app.core.auth.user import AuthUser


def _household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]


def _as(client, subject: str, email: str) -> None:
    client.app.dependency_overrides[deps.get_current_user] = lambda: AuthUser(
        subject=subject,
        email=email,
        name=email.split("@")[0].title(),
        scopes=ALL_SCOPES,
    )


def _link_adult(client, household_id: str) -> str:
    created = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "adult",
            "first_name": "Sam",
            "last_name": "Helper",
            "email": "sam@example.com",
        },
    )
    assert created.status_code == 201, created.text
    member_id = created.json()["id"]
    _as(client, "sub-sam", "sam@example.com")
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["linked"] is True
    _as(client, "sub-ada", "ada@example.com")
    return member_id


def test_permission_catalog_lists_tabs_and_form_actions(client) -> None:
    response = client.get("/api/permission-catalog")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "tab.school" in codes
    assert "tab.discipline" in codes
    assert "tab.documents" in codes
    assert "tab.export" in codes
    assert "form.sibling_contact" in codes
    sibling = next(
        item for item in response.json() if item["code"] == "form.sibling_contact"
    )
    assert set(sibling["actions"]) == {"view", "add", "edit", "export"}
    school = next(item for item in response.json() if item["code"] == "tab.school")
    assert "view" in school["actions"]
    assert "add" in school["actions"]
    assert "edit" in school["actions"]


def test_admin_can_grant_and_read_member_permissions(client) -> None:
    household_id = _household(client)
    member_id = _link_adult(client, household_id)
    granted = client.put(
        f"/api/households/{household_id}/members/{member_id}/permissions",
        json={
            "grants": [
                {"resource": "tab.school", "action": "view"},
                {"resource": "form.sibling_contact", "action": "add"},
                {"resource": "form.sibling_contact", "action": "view"},
            ]
        },
    )
    assert granted.status_code == 200, granted.text
    listing = client.get(
        f"/api/households/{household_id}/members/{member_id}/permissions"
    )
    assert listing.status_code == 200
    pairs = {(item["resource"], item["action"]) for item in listing.json()}
    assert ("tab.school", "view") in pairs
    assert ("form.sibling_contact", "add") in pairs


def test_adult_without_grants_cannot_add_sibling_contact(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    _link_adult(client, household_id)
    _as(client, "sub-sam", "sam@example.com")
    response = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "sibling_contact",
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "payload": {
                "date": "2026-08-19",
                "start_time": "16:30",
                "end_time": "17:00",
                "siblings_in_home": [child_id],
                "contact_type": "Phone call",
            },
        },
    )
    assert response.status_code == 403


def test_adult_with_form_add_can_create_sibling_contact(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    member_id = _link_adult(client, household_id)
    client.put(
        f"/api/households/{household_id}/members/{member_id}/permissions",
        json={
            "grants": [
                {"resource": "tab.logs", "action": "view"},
                {"resource": "form.sibling_contact", "action": "add"},
            ]
        },
    )
    _as(client, "sub-sam", "sam@example.com")
    response = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "sibling_contact",
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "start_time": "16:30",
                "end_time": "17:00",
                "siblings_in_home": [child_id],
                "contact_type": "Phone call",
            },
        },
    )
    assert response.status_code == 201, response.text


def test_adult_without_school_view_cannot_list_enrollments(client) -> None:
    household_id = _household(client)
    _link_adult(client, household_id)
    _as(client, "sub-sam", "sam@example.com")
    response = client.get(f"/api/households/{household_id}/enrollments")
    assert response.status_code == 403


def test_non_admin_cannot_change_permissions(client) -> None:
    household_id = _household(client)
    member_id = _link_adult(client, household_id)
    _as(client, "sub-sam", "sam@example.com")
    response = client.put(
        f"/api/households/{household_id}/members/{member_id}/permissions",
        json={"grants": [{"resource": "tab.school", "action": "view"}]},
    )
    assert response.status_code == 403


def test_me_includes_effective_household_permissions(client) -> None:
    household_id = _household(client)
    member_id = _link_adult(client, household_id)
    client.put(
        f"/api/households/{household_id}/members/{member_id}/permissions",
        json={"grants": [{"resource": "tab.documents", "action": "view"}]},
    )
    _as(client, "sub-sam", "sam@example.com")
    me = client.get("/api/me").json()
    home = next(item for item in me["households"] if item["id"] == household_id)
    assert home["household_role"] == "adult"
    assert home["member_id"] == member_id
    pairs = {(item["resource"], item["action"]) for item in home["permissions"]}
    assert ("tab.documents", "view") in pairs
    assert ("tab.school", "view") not in pairs
