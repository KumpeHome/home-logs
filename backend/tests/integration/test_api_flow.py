from datetime import UTC, datetime


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_household_and_pending_member(client) -> None:
    created = client.post(
        "/api/households",
        json={"name": "Kumpe Home", "household_type": "foster"},
    )
    assert created.status_code == 201
    household_id = created.json()["id"]

    child = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "child",
            "first_name": "Casey",
            "last_name": "Child",
            "date_of_birth": "2014-04-02",
        },
    )
    assert child.status_code == 201
    assert child.json()["login_status"] == "none"
    assert child.json()["status"] == "active"

    adult = client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "adult",
            "first_name": "Riley",
            "last_name": "Caregiver",
            "email": "riley@example.com",
            "invite": True,
            "idp_role": "Caregiver",
        },
    )
    assert adult.status_code == 201
    assert adult.json()["login_status"] == "pending"


def test_first_login_links_pending_member(client, sqlite_engine, actor) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]
    client.post(
        f"/api/households/{household_id}/members",
        json={
            "household_role": "adult",
            "first_name": "Riley",
            "last_name": "Care",
            "email": "riley@example.com",
            "invite": True,
        },
    )
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.api import deps
    from app.core.auth.scopes import ALL_SCOPES
    from app.core.auth.user import AuthUser
    from app.db.session import get_db
    from app.main import create_app

    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)

    def override_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    riley = AuthUser(
        subject="sub-riley",
        email="riley@example.com",
        scopes=ALL_SCOPES,
    )
    application = create_app(init_db=False)
    application.dependency_overrides[get_db] = override_db
    application.dependency_overrides[deps.get_current_user] = lambda: riley
    with TestClient(application) as riley_client:
        me = riley_client.get("/api/me")
        assert me.status_code == 200
        assert me.json()["linked"] is True
        members = riley_client.get(f"/api/households/{household_id}/members").json()
        riley_row = next(
            item for item in members if item["email"] == "riley@example.com"
        )
        assert riley_row["login_status"] == "linked"
        assert riley_row["auth_subject"] == "sub-riley"

    response = client.get("/api/form-types")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "case_worker_visit" in codes
    assert "medication_administration" in codes


def test_profile_medication_and_mar(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "mixed"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med = client.post(
        f"/api/households/{household_id}/members/{member_id}/medications",
        json={
            "name": "Cetirizine",
            "dose": "5mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
            "instructions": "With breakfast",
            "prescriber": "Dr. Lee",
            "is_psychotropic": False,
        },
    )
    assert med.status_code == 200
    med_id = med.json()["id"]
    log = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": member_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Cetirizine",
                "quantity_given": 1,
                "dose_given": "5mg",
                "outcome": "given",
            },
        },
    )
    assert log.status_code == 201, log.text
    fire = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "fire_drill",
            "occurred_at": datetime.now(UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "start_time": "10:00",
                "end_time": "10:04",
                "evacuation_seconds": "47",
                "participants": ["Ada", "Sam"],
                "alarm_tested": True,
            },
        },
    )
    assert fire.status_code == 201, fire.text
    viewed = client.get(f"/api/households/{household_id}/logs/{fire.json()['id']}")
    assert viewed.status_code == 200
    assert viewed.json()["form_type_code"] == "fire_drill"
    assert viewed.json()["payload"]["date"] == "2026-08-19"
    assert viewed.json()["payload"]["evacuation_seconds"] == 47
    exported = client.get(f"/api/households/{household_id}/logs-export?format=csv")
    assert exported.status_code == 200
    assert b"fire_drill" in exported.content


def test_psychotropic_mar_does_not_require_witness(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{member_id}/medications",
        json={
            "name": "Sertraline",
            "dose": "25mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
            "is_psychotropic": True,
        },
    ).json()["id"]
    log = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": member_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "quantity_given": 1,
                "outcome": "given",
            },
        },
    )
    assert log.status_code == 201, log.text


def test_inactive_members_hidden_by_default(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Lea", "last_name": "Out"},
    ).json()["id"]
    client.post(
        f"/api/households/{household_id}/members/{member_id}/deactivate",
        json={"reason": "Placement ended"},
    )
    active = client.get(f"/api/households/{household_id}/members").json()
    names = [item["first_name"] for item in active]
    assert "Lea" not in names
    all_members = client.get(
        f"/api/households/{household_id}/members?include_inactive=true"
    ).json()
    assert any(item["first_name"] == "Lea" for item in all_members)


def test_discipline_and_grades(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Jordan", "last_name": "Lee"},
    ).json()["id"]
    disc = client.post(
        f"/api/households/{household_id}/discipline",
        json={
            "member_id": member_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "location": "Kitchen",
            "antecedent": "Asked to do homework",
            "behavior": "Threw pencil",
            "intervention": "Cool-down in room",
            "consequence": "Lost screen time",
            "duration_minutes": 15,
            "follow_up": "Talk after dinner",
            "notified": ["Case worker"],
        },
    )
    assert disc.status_code == 201, disc.text
    enrollment = client.post(
        f"/api/households/{household_id}/enrollments",
        json={
            "member_id": member_id,
            "school_name": "Lincoln Elementary",
            "grade_level": "4",
            "school_year": "2026-2027",
            "iep": True,
        },
    )
    assert enrollment.status_code == 201
    grade = client.post(
        f"/api/households/{household_id}/enrollments/{enrollment.json()['id']}/grades",
        json={"term": "Q1", "course": "Math", "letter": "B", "percent": "84"},
    )
    assert grade.status_code == 200
    dash = client.get(f"/api/households/{household_id}/dashboard")
    assert dash.status_code == 200
    assert dash.json()["active_members"] >= 1


def test_household_otc_catalog_assignable_to_member(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/otc-medications",
        json={
            "name": "Acetaminophen",
            "dose": "325mg",
            "route": "oral",
            "instructions": "As needed for fever",
        },
    )
    assert created.status_code == 201, created.text
    otc_id = created.json()["id"]
    catalog = client.get(f"/api/households/{household_id}/otc-medications")
    assert catalog.status_code == 200
    names = [item["name"] for item in catalog.json()]
    assert "Acetaminophen" in names

    assigned = client.post(
        f"/api/households/{household_id}/members/{member_id}/otc-medications",
        json={"otc_medication_id": otc_id},
    )
    assert assigned.status_code == 201, assigned.text
    assignment_id = assigned.json()["id"]
    profile = client.get(
        f"/api/households/{household_id}/members/{member_id}/profile"
    ).json()
    otc_names = [item["name"] for item in profile["otc_medications"]]
    assert "Acetaminophen" in otc_names
    assert all(item.get("is_otc") for item in profile["otc_medications"])
    assert profile["medications"] == []

    log = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": member_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": assignment_id,
                "medication_name": "Acetaminophen",
                "quantity_given": 1,
                "dose_given": "325mg",
                "outcome": "given",
            },
        },
    )
    assert log.status_code == 201, log.text

    duplicate = client.post(
        f"/api/households/{household_id}/members/{member_id}/otc-medications",
        json={"otc_medication_id": otc_id},
    )
    assert duplicate.status_code == 400


def test_update_medication_flags_dates_and_reject_expired_mar(client) -> None:
    household_id = client.post(
        "/api/households", json={"name": "Home", "household_type": "family"}
    ).json()["id"]
    member_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/members/{member_id}/medications",
        json={
            "name": "Amoxicillin",
            "dose": "400mg",
            "route": "oral",
            "frequency": "twice daily",
            "schedule_times": ["08:00", "20:00"],
            "instructions": "Finish the bottle",
            "prescriber": "Dr. Patel",
            "diagnosis": "Ear infection",
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
            "flags": ["drowsy", "take_with_food"],
        },
    )
    assert created.status_code == 200, created.text
    med_id = created.json()["id"]
    profile = client.get(
        f"/api/households/{household_id}/members/{member_id}/profile"
    ).json()
    med = next(item for item in profile["medications"] if item["id"] == med_id)
    assert med["flags"] == ["drowsy", "take_with_food"]
    assert med["start_date"] == "2026-08-01"
    assert med["end_date"] == "2026-08-10"
    assert med["diagnosis"] == "Ear infection"

    updated = client.patch(
        f"/api/households/{household_id}/members/{member_id}/medications/{med_id}",
        json={
            "end_date": "2026-08-12",
            "active": True,
            "flags": ["drowsy", "take_with_food", "shake_well"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["end_date"] == "2026-08-12"
    assert "shake_well" in updated.json()["flags"]

    expired = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": member_id,
            "occurred_at": "2026-08-19T12:00:00+00:00",
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Amoxicillin",
                "quantity_given": 1,
                "dose_given": "400mg",
                "outcome": "given",
            },
        },
    )
    assert expired.status_code == 400
    assert (
        "window" in expired.json()["detail"].lower()
        or "date" in expired.json()["detail"].lower()
    )
