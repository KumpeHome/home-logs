from datetime import UTC, datetime, timedelta
from io import BytesIO

from pypdf import PdfReader

from app.exports.ar_dcfs_forms import journal_entries_pdf


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
        "ar_dcfs_weekly_med_chart",
        "ar_dcfs_sibling_contact",
        "ar_dcfs_journal_entries",
        "ar_dcfs_personal_belonging",
        "ar_dcfs_foster_home_log",
    }
    names = {item["name"] for item in rows}
    assert "Quarterly Fire/Tornado Drills" in names
    assert "Medication Dosage Logs" in names
    assert "Weekly Medication Chart" in names
    assert "Separated Sibling Contact Report" in names
    assert "Journal Entries" in names
    assert "Personal Belonging Inventory Log" in names
    assert "Foster Home Log" in names
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


def _med_child(client) -> tuple[str, str, str]:
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
    return household_id, child_id, med_id


def test_export_weekly_med_chart_groups_doses_by_week(client) -> None:
    household_id, child_id, med_id = _med_child(client)
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 13, 15, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Cetirizine",
                "quantity_given": 1,
                "dose_given": "5mg",
                "outcome": "given",
                "fp_initials": "JK",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_weekly_med_chart",
            "start_date": "2026-08-16",
            "end_date": "2026-08-22",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    page = PdfReader(BytesIO(response.content)).pages[0]
    assert float(page.mediabox.width) > float(page.mediabox.height)
    text = _pdf_text(response.content)
    assert "Weekly Medication Chart" in text
    assert "CFS-372" in text
    assert "03/2021" in text
    assert "Sam Kid" in text
    assert "Cetirizine" in text
    assert "5mg" in text
    assert "daily" in text
    assert "SUNDAY" in text
    assert "WEDNESDAY" in text
    assert "8:15 AM" in text
    assert "JK" in text


def test_export_weekly_med_chart_embeds_drawn_initials(client) -> None:
    household_id, child_id, med_id = _med_child(client)
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "medication_administration",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 13, 15, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "medication_id": med_id,
                "medication_name": "Cetirizine",
                "quantity_given": 1,
                "dose_given": "5mg",
                "outcome": "given",
                "fp_initials": TINY_PNG,
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_weekly_med_chart",
            "start_date": "2026-08-16",
            "end_date": "2026-08-22",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    assert b"/XObject" in response.content
    assert "data:image" not in _pdf_text(response.content)


def test_export_journal_entries_pdf_includes_child_and_incident(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "journal_entry",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 21, 30, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-19",
                "time": "16:30",
                "incident": "Small scrape on left knee after soccer.",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_journal_entries",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "Journal Entries" in text
    assert "bruises, scrapes, cuts" in text
    assert "Casey Child" in text
    assert "Small scrape on left knee after soccer." in text
    assert "2026-08-19" in text or "08-19-26" in text or "8/19" in text
    assert "Date" in text
    assert "Time" in text
    assert "Incident" in text


def test_export_journal_entries_paginates_after_eight_rows(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    for index in range(9):
        created = client.post(
            f"/api/households/{household_id}/logs",
            json={
                "form_type_code": "journal_entry",
                "subject_member_id": child_id,
                "occurred_at": datetime(
                    2026, 8, 1 + index, 21, 30, tzinfo=UTC
                ).isoformat(),
                "submit": True,
                "payload": {
                    "date": f"2026-08-{index + 1:02d}",
                    "time": "16:30",
                    "incident": f"Journal row {index + 1} unique note.",
                },
            },
        )
        assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_journal_entries",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    pages = PdfReader(BytesIO(response.content)).pages
    assert len(pages) == 2
    first = pages[0].extract_text() or ""
    second = pages[1].extract_text() or ""
    assert "Journal row 1 unique note." in first
    assert "Journal row 8 unique note." in first
    assert "Journal row 9 unique note." not in first
    assert "Journal row 9 unique note." in second
    assert "Casey Child" in second


def test_journal_entries_keeps_three_incident_lines_in_one_row() -> None:
    long_entry = (
        "First unique scrape line after soccer.\n"
        "Second unique scrape line after soccer.\n"
        "Third unique scrape line after soccer."
    )
    rows = [("2026-08-01", "4:30 PM", long_entry)]
    rows.extend(
        (
            f"2026-08-{index + 2:02d}",
            "4:30 PM",
            f"Short journal note {index + 1} unique.",
        )
        for index in range(7)
    )
    pages = PdfReader(BytesIO(journal_entries_pdf([("Casey Child", rows)]))).pages
    assert len(pages) == 1
    text = pages[0].extract_text() or ""
    assert "First unique scrape line after soccer." in text
    assert "Third unique scrape line after soccer." in text
    assert "Short journal note 7 unique." in text


def test_journal_entries_overflow_line_expands_into_next_row() -> None:
    long_entry = (
        "First unique scrape line after soccer.\n"
        "Second unique scrape line after soccer.\n"
        "Third unique scrape line after soccer.\n"
        "Fourth unique scrape line after soccer."
    )
    rows = [("2026-08-01", "4:30 PM", long_entry)]
    rows.extend(
        (
            f"2026-08-{index + 2:02d}",
            "4:30 PM",
            f"Short journal note {index + 1} unique.",
        )
        for index in range(7)
    )
    pages = PdfReader(BytesIO(journal_entries_pdf([("Casey Child", rows)]))).pages
    assert len(pages) == 2
    first = pages[0].extract_text() or ""
    second = pages[1].extract_text() or ""
    assert "Fourth unique scrape line after soccer." in first
    assert "Short journal note 6 unique." in first
    assert "Short journal note 7 unique." not in first
    assert "Short journal note 7 unique." in second


def test_journal_entries_word_wraps_long_incident_onto_extra_rows() -> None:
    incident = " ".join(f"WrapToken{index:02d}" for index in range(80))
    rows = [("2026-08-01", "4:30 PM", incident)]
    rows.extend(
        (
            f"2026-08-{index + 2:02d}",
            "4:30 PM",
            f"Short journal note {index + 1} unique.",
        )
        for index in range(7)
    )
    pdf = journal_entries_pdf([("Casey Child", rows)])
    pages = PdfReader(BytesIO(pdf)).pages
    assert len(pages) >= 2
    text = _pdf_text(pdf)
    for index in range(80):
        assert f"WrapToken{index:02d}" in text
    first = pages[0].extract_text() or ""
    second = pages[1].extract_text() or ""
    assert "Short journal note 7 unique." in second
    assert "Short journal note 7 unique." not in first


def test_export_personal_belonging_pdf_matches_cfs350(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "personal_belonging",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 8, 19, 15, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "item_category": "Shoes",
                "description": "Nike size 5",
                "quantity": 1,
                "recorded_on": "2026-08-19",
                "initials": "JK",
                "disposition": "",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_personal_belonging",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "CFS-350" in text
    assert "01/2021" in text
    assert "Division of Children and Family Services" in text
    assert "Personal Belonging Inventory Log" in text
    assert "Sam Kid" in text
    assert "Shoes" in text
    assert "Nike size 5" in text
    assert "Pairs of Socks" in text


def test_export_personal_belonging_other_row_uses_short_label(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "personal_belonging",
            "subject_member_id": child_id,
            "occurred_at": datetime(2026, 9, 4, 15, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "item_category": "Other",
                "description": "Black pillow case",
                "quantity": 1,
                "recorded_on": "2026-09-04",
                "initials": "JK",
            },
        },
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_personal_belonging",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "Other" in text
    assert "Black pillow case" in text
    assert "list any other personal possessions" not in text
    assert "makeup" not in text


def _child(client, household_id: str) -> str:
    return client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]


def _add_belonging(
    client,
    household_id: str,
    child_id: str,
    *,
    category: str,
    description: str,
    index: int,
) -> None:
    occurred = datetime(2026, 8, 1, 15, 0, tzinfo=UTC) + timedelta(minutes=index)
    created = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "personal_belonging",
            "subject_member_id": child_id,
            "occurred_at": occurred.isoformat(),
            "submit": True,
            "payload": {
                "item_category": category,
                "description": description,
                "quantity": 1,
                "recorded_on": occurred.date().isoformat(),
                "initials": "JK",
            },
        },
    )
    assert created.status_code == 201, created.text


def _export_belonging(client, household_id: str, child_id: str):
    return client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_personal_belonging",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )


def test_export_personal_belonging_other_items_fill_first_page(client) -> None:
    household_id = _household(client)
    child_id = _child(client, household_id)
    for index in range(8):
        _add_belonging(
            client,
            household_id,
            child_id,
            category="Other",
            description=f"Other item {index + 1}",
            index=index,
        )
    response = _export_belonging(client, household_id, child_id)
    assert response.status_code == 200, response.text
    pages = PdfReader(BytesIO(response.content)).pages
    assert len(pages) == 1
    text = pages[0].extract_text() or ""
    for index in range(8):
        assert f"Other item {index + 1}" in text


def test_export_personal_belonging_other_overflows_after_page_is_full(client) -> None:
    household_id = _household(client)
    child_id = _child(client, household_id)
    total = 40
    for index in range(total):
        _add_belonging(
            client,
            household_id,
            child_id,
            category="Other",
            description=f"Packed item {index + 1}",
            index=index,
        )
    response = _export_belonging(client, household_id, child_id)
    assert response.status_code == 200, response.text
    pages = PdfReader(BytesIO(response.content)).pages
    assert len(pages) >= 2
    first = pages[0].extract_text() or ""
    rest = "".join(page.extract_text() or "" for page in pages[1:])
    first_count = sum(
        1 for index in range(total) if f"Packed item {index + 1}" in first
    )
    assert first_count > 4
    assert "Packed item 1" in first
    assert f"Packed item {total}" not in first
    assert f"Packed item {total}" in rest


def test_export_personal_belonging_overflow_shoes_go_to_next_page(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Sam", "last_name": "Kid"},
    ).json()["id"]
    for index in range(5):
        created = client.post(
            f"/api/households/{household_id}/logs",
            json={
                "form_type_code": "personal_belonging",
                "subject_member_id": child_id,
                "occurred_at": datetime(
                    2026, 8, 1 + index, 15, 0, tzinfo=UTC
                ).isoformat(),
                "submit": True,
                "payload": {
                    "item_category": "Shoes",
                    "description": f"Shoe pair {index + 1}",
                    "quantity": 1,
                    "recorded_on": f"2026-08-{index + 1:02d}",
                    "initials": "JK",
                },
            },
        )
        assert created.status_code == 201, created.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_personal_belonging",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [child_id],
        },
    )
    assert response.status_code == 200, response.text
    pages = PdfReader(BytesIO(response.content)).pages
    assert len(pages) == 2
    first = pages[0].extract_text() or ""
    second = pages[1].extract_text() or ""
    assert "Shoe pair 1" in first
    assert "Shoe pair 4" in first
    assert "Shoe pair 5" not in first
    assert "Shoe pair 5" in second
    assert "CFS-350" in second


def test_export_foster_home_log_summarizes_the_month(client) -> None:
    household_id = _household(client)
    child_id = client.post(
        f"/api/households/{household_id}/members",
        json={"household_role": "child", "first_name": "Casey", "last_name": "Child"},
    ).json()["id"]
    training = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "training",
            "occurred_at": datetime(2026, 8, 4, 18, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "date": "2026-08-04",
                "topic": "CPR / First Aid",
                "hours": "2",
                "notes": "Agency in-service",
            },
        },
    )
    assert training.status_code == 201, training.text
    drill = client.post(
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
    assert drill.status_code == 201, drill.text
    visit = client.post(
        f"/api/households/{household_id}/logs",
        json={
            "form_type_code": "case_worker_visit",
            "occurred_at": datetime(2026, 8, 21, 16, 0, tzinfo=UTC).isoformat(),
            "submit": True,
            "payload": {
                "children_visited": [child_id],
                "worker_name": "Lee Worker",
                "visit_type": "home",
                "topics": "School",
            },
        },
    )
    assert visit.status_code == 201, visit.text
    response = client.post(
        f"/api/households/{household_id}/form-exports",
        json={
            "form_code": "ar_dcfs_foster_home_log",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "member_ids": [],
        },
    )
    assert response.status_code == 200, response.text
    text = _pdf_text(response.content)
    assert "FOSTER HOME LOG" in text
    assert "AUGUST" in text
    assert "TRAINING" in text
    assert "CPR / First Aid" in text
    assert "FIRE DRILLS" in text
    assert "Casey Child" in text
    assert "47" in text
    assert "WORKER VISITS" in text
    assert "Lee Worker" in text
