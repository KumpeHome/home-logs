from app.forms.catalog import FORM_TYPES, get_form_type
from app.forms.validate import normalize_payload, validate_payload


def html_like_minimal_payload(schema: dict) -> dict:
    payload: dict = {}
    for key in schema.get("required", []):
        spec = schema["properties"][key]
        kind = spec.get("type")
        if kind == "integer":
            payload[key] = "12"
        elif kind == "boolean":
            continue
        elif kind == "array":
            payload[key] = "Ada, Casey"
        elif spec.get("enum"):
            payload[key] = spec["enum"][0]
        elif spec.get("format") == "date":
            payload[key] = "2026-08-19"
        elif spec.get("format") == "time":
            payload[key] = "10:00"
        elif spec.get("format") == "date-time":
            payload[key] = "2026-08-19T10:00"
        else:
            payload[key] = "ok"
    return payload


def test_html_fire_drill_payload_coerces_string_seconds_and_passes() -> None:
    form = get_form_type("fire_drill")
    errors = validate_payload(
        form.schema,
        normalize_payload(
            form.schema,
            {
                "date": "2026-08-19",
                "start_time": "10:00",
                "end_time": "10:04",
                "evacuation_seconds": "47",
                "participants": ["member-ada"],
                "notes": "",
            },
        ),
    )
    assert errors == []


def test_every_catalog_form_accepts_html_like_minimal_payload() -> None:
    for form in FORM_TYPES:
        if form.code == "medication_administration":
            continue
        payload = html_like_minimal_payload(form.schema)
        errors = validate_payload(form.schema, normalize_payload(form.schema, payload))
        assert errors == [], f"{form.code}: {errors} payload={payload}"


def test_catalog_includes_required_home_and_foster_forms() -> None:
    codes = {item.code for item in FORM_TYPES}
    for expected in {
        "fire_drill",
        "tornado_drill",
        "case_worker_visit",
        "medication_administration",
        "daily_care",
        "family_visit",
        "court_hearing",
        "incident",
        "reasonable_prudent_parenting",
        "sibling_contact",
    }:
        assert expected in codes


def test_sibling_contact_collects_official_cfs400_fields() -> None:
    form = get_form_type("sibling_contact")
    props = form.schema["properties"]
    assert form.scope == "household"
    assert props["date"]["format"] == "date"
    assert props["start_time"]["format"] == "time"
    assert props["end_time"]["format"] == "time"
    assert props["siblings_in_home"]["x-widget"] == "child-multiselect"
    assert props["contact_type"]["enum"] == [
        "Face-to-face",
        "Phone call",
        "Text",
        "Video (Skype / FaceTime)",
        "Other",
    ]
    for key in ("date", "start_time", "end_time", "siblings_in_home", "contact_type"):
        assert key in form.schema["required"]


def _drill_payload(**overrides: object) -> dict:
    payload: dict = {
        "date": "2026-08-19",
        "start_time": "10:00",
        "end_time": "10:04",
        "evacuation_seconds": 47,
        "participants": ["member-ada", "member-casey"],
    }
    payload.update(overrides)
    return payload


def test_fire_drill_requires_evacuation_fields() -> None:
    form = get_form_type("fire_drill")
    errors = validate_payload(
        form.schema,
        {"location": "Kitchen", "participants": ["Ada"], "notes": "ok"},
    )
    assert errors


def test_fire_drill_schema_uses_date_times_seconds_and_member_select() -> None:
    props = get_form_type("fire_drill").schema["properties"]
    assert props["date"]["format"] == "date"
    assert props["start_time"]["format"] == "time"
    assert props["end_time"]["format"] == "time"
    assert props["evacuation_seconds"]["type"] == "integer"
    assert props["evacuation_seconds"]["minimum"] == 0
    assert props["participants"]["x-widget"] == "member-multiselect"
    assert props["participants"]["format"] == "member-ids"


def test_valid_fire_drill_payload_passes() -> None:
    form = get_form_type("fire_drill")
    errors = validate_payload(form.schema, _drill_payload())
    assert errors == []


def test_tornado_drill_schema_matches_fire_drill_core_fields() -> None:
    fire = get_form_type("fire_drill").schema["properties"]
    tornado = get_form_type("tornado_drill").schema["properties"]
    for key in ("date", "start_time", "end_time", "evacuation_seconds", "participants"):
        assert tornado[key] == fire[key]


def test_valid_tornado_drill_payload_passes() -> None:
    form = get_form_type("tornado_drill")
    errors = validate_payload(form.schema, _drill_payload(evacuation_seconds=32))
    assert errors == []


def test_medication_admin_requires_quantity_and_omits_witness() -> None:
    form = get_form_type("medication_administration")
    props = form.schema["properties"]
    assert "witness_name" not in props
    assert props["quantity_given"]["type"] == "integer"
    assert "quantity_given" in form.schema["required"]
    assert "fp_initials" in props
    assert "fc_initials" in props
    assert "fp_initials" not in form.schema["required"]
    assert "fc_initials" not in form.schema["required"]


def test_drill_rejects_negative_evacuation_seconds() -> None:
    form = get_form_type("fire_drill")
    errors = validate_payload(form.schema, _drill_payload(evacuation_seconds=-1))
    assert errors


def _visit_children_field(code: str) -> dict:
    return get_form_type(code).schema["properties"]["children_visited"]


def test_visit_forms_use_multi_select_for_children_visited() -> None:
    for code in ("case_worker_visit", "family_visit"):
        field = _visit_children_field(code)
        assert field["type"] == "array"
        assert field["uniqueItems"] is True
        assert field["x-widget"] == "child-multiselect"
        assert "children_visited" in get_form_type(code).schema["required"]
        assert get_form_type(code).scope == "household"


def test_case_worker_visit_accepts_multiple_children() -> None:
    form = get_form_type("case_worker_visit")
    errors = validate_payload(
        form.schema,
        {
            "worker_name": "Lee Worker",
            "visit_type": "home",
            "topics": "School and medical",
            "children_visited": ["child-1", "child-2"],
        },
    )
    assert errors == []


def test_family_visit_accepts_multiple_children() -> None:
    form = get_form_type("family_visit")
    errors = validate_payload(
        form.schema,
        {
            "visitors": ["Jordan Parent"],
            "location": "Agency",
            "started_at": "2026-08-19T14:00:00",
            "ended_at": "2026-08-19T15:00:00",
            "supervised": True,
            "children_visited": ["child-1", "child-2"],
        },
    )
    assert errors == []
