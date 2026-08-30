from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader


def _household(client) -> str:
    return client.post(
        "/api/households", json={"name": "Home", "household_type": "foster"}
    ).json()["id"]


def _pdf_text(content: bytes) -> str:
    return "".join(
        (page.extract_text() or "") for page in PdfReader(BytesIO(content)).pages
    )


def test_export_forms_lists_official_ar_dcfs_forms(client) -> None:
    response = client.get("/api/export-forms")
    assert response.status_code == 200
    rows = response.json()
    codes = {item["code"] for item in rows}
    assert codes == {
        "ar_dcfs_quarterly_drills",
        "ar_dcfs_medication_log",
        "ar_dcfs_sibling_contact",
    }
    names = {item["name"] for item in rows}
    assert "Quarterly Fire/Tornado Drills" in names
    assert "Medication Dosage Logs" in names
    assert "Separated Sibling Contact Report" in names
    assert {item["category"] for item in rows} == {"Arkansas DCFS"}
    for item in rows:
        assert item["code"].startswith("ar_dcfs")


def test_export_quarterly_drills_pdf_includes_date_and_participant(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "fire_drill",
            "occurred_at": datetime(2026, 8, 19, 15, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "start_time": "10:00",
                "end_time": "10:04",
                "evacuation_seconds": "47",
                "participants": [child_id],
                "alarm_tested": True,
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_quarterly_drills",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    text = _pdf_text(response.content)
    assert "Quarterly Fire/Tornado Drills" in text
    assert "Casey Child" in text
    assert "47" in text


def test_export_quarterly_drills_includes_every_participant(client) -> None:
    household_id = _household(client)
    casey_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    ada_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "adult", "first_name": "Ada", "last_name": "Admin"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "fire_drill",
            "occurred_at": datetime(2026, 8, 19, 15, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "start_time": "10:00",
                "end_time": "10:04",
                "evacuation_seconds": "47",
                "participants": [casey_id, ada_id],
                "alarm_tested": True,
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_quarterly_drills",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [casey_id],
        },
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "Casey Child" in text
    assert "Ada Admin" in text


def test_export_medication_log_pdf_includes_child_name_and_dose(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Cetirizine",
            "dose": "5mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
        },
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 20, 8, 15, tzinfo=UTC).isoformat(),
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
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_medication_log",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    text = _pdf_text(response.content)
    assert "MEDICATION DOSAGE LOGS" in text
    assert "Sam Kid" in text
    assert "Cetirizine" in text
    assert "5mg" in text


def test_export_medication_log_multiplies_unit_dose_by_number_given(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Melatonin",
            "dose": "1mg",
            "route": "oral",
            "frequency": "nightly",
            "schedule_times": ["20:00"],
        },
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 20, 20, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Melatonin",
                "quantity_given": 2,
                "outcome": "given",
            },
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["payload"]["dose_given"] == "2mg"
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_medication_log",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert "2mg" in _pdf_text(response.content)


def test_export_medication_log_includes_child_initials(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Cetirizine",
            "dose": "5mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
        },
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 20, 8, 15, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Cetirizine",
                "quantity_given": 1,
                "outcome": "given",
                "fc_initials": "SK",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_medication_log",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert "SK" in _pdf_text(response.content)


TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_export_medication_log_embeds_drawn_initials(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Cetirizine",
            "dose": "5mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["08:00"],
        },
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 20, 8, 15, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "quantity_given": 1,
                "outcome": "given",
                "fp_initials": TINY_PNG,
                "fc_initials": TINY_PNG,
            },
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["payload"]["fp_initials"] == TINY_PNG
    assert created.json()["payload"]["fc_initials"] == TINY_PNG
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_medication_log",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    assert b"/Image" in response.content


def test_export_medication_log_uses_household_timezone(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    med_id = client.post(
        f"/api/households/{household_id}/members/{child_id}/medications",
        json={
            "name": "Cetirizine",
            "dose": "5mg",
            "route": "oral",
            "frequency": "daily",
            "schedule_times": ["20:27"],
        },
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": "2026-08-30T01:27:00.000Z",
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "quantity_given": 1,
                "outcome": "given",
            },
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["occurred_at"].endswith("Z")
    same_day = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_medication_log",
            "start_date": "2026-08-29",
            "end_date": "2026-08-29",
            "member_ids": [child_id],
        },
    )
    assert same_day.status_code == 200, same_day.text
    text = _pdf_text(same_day.content)
    assert "2026-08-29" in text
    assert "8:27 PM" in text
    assert "20:27" not in text
    assert "01:27" not in text


def _sibling_household(client) -> tuple[str, str, str]:
    household_id = client.post(
        "/api/households",
        json={
            "name": "Kumpe Home",
            "household_type": "foster",
            "license_number": "FP-1234",
        },
    ).json()["id"]
    casey_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    sam_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    return household_id, casey_id, sam_id


def _add_sibling_contact(
    client,
    household_id: str,
    siblings_in_home: list[str],
    *,
    date: str,
    notes: str,
    other: str,
) -> None:
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "sibling_contact",
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": date,
                "start_time": "16:30",
                "end_time": "17:00",
                "siblings_in_home": siblings_in_home,
                "other_siblings": [other],
                "contact_type": "Phone call",
                "notes": notes,
            },
        },
    )
    assert created.status_code == 201, created.text


def _filled_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    text = _pdf_text(content)
    fields = reader.get_fields() or {}
    values = []
    for field in fields.values():
        value = field.get("/V")
        if value:
            values.append(str(value))
    return f"{text}\n{' '.join(values)}"


def test_export_sibling_contact_pdf_matches_official_cfs400(client) -> None:
    household_id, casey_id, _sam_id = _sibling_household(client)
    _add_sibling_contact(
        client,
        household_id,
        [casey_id],
        date="2026-08-19",
        notes="Casey told Johnny about the science fair.",
        other="Johnny Smith",
    )
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_sibling_contact",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [casey_id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    page = PdfReader(BytesIO(response.content)).pages[0]
    assert float(page.mediabox.width) > float(page.mediabox.height)
    text = _filled_pdf_text(response.content)
    assert "CFS-400 (01/2016)" in text
    assert "ARKANSAS DEPARTMENT OF HUMAN SERVICES" in text
    assert "Sibling relationships are critically important" in text
    assert "Susie Smith" not in text
    assert "Star Wars" not in text
    assert "school play" not in text
    assert "Kumpe Home / FP-1234" in text
    assert "Casey Child" in text
    assert "Johnny Smith" in text
    assert "Phone call" in text
    assert "science fair" in text
    assert "08-19-26 @ 4:30 p.m.-5:00 p.m." in text
    heights: list[float] = []

    def _visit(text: str, _cm, tm, _font_dict, _font_size) -> None:
        if "08-19-26" in (text or ""):
            heights.append(float(tm[5]))

    page.extract_text(visitor_text=_visit)
    assert heights
    assert max(heights) > 330


def test_export_sibling_contact_only_includes_selected_child(client) -> None:
    household_id, casey_id, sam_id = _sibling_household(client)
    _add_sibling_contact(
        client,
        household_id,
        [casey_id],
        date="2026-08-19",
        notes="Casey science fair call.",
        other="Johnny Smith",
    )
    _add_sibling_contact(
        client,
        household_id,
        [sam_id],
        date="2026-08-20",
        notes="Sam soccer recap.",
        other="Riley Jones",
    )
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_sibling_contact",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [casey_id],
        },
    )
    assert response.status_code == 200, response.text
    text = _filled_pdf_text(response.content)
    assert "Casey science fair call." in text
    assert "Sam soccer recap." not in text
    assert "Riley Jones" not in text


def test_export_rejects_unknown_form_code(client) -> None:
    household_id = _household(client)
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "not_a_form",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [],
        },
    )
    assert response.status_code == 400
