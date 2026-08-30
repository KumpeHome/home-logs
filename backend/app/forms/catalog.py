from __future__ import annotations

from dataclasses import dataclass, field

from app.core.errors import DomainError


@dataclass(frozen=True)
class FormType:
    code: str
    name: str
    category: str
    scope: str  # household | member
    description: str
    schema: dict
    export_paths: tuple[str, ...] = field(default_factory=tuple)


def _string(title: str, **extra: object) -> dict:
    return {"type": "string", "title": title, **extra}


def _bool(title: str) -> dict:
    return {"type": "boolean", "title": title}


def _array(title: str, item_type: str = "string") -> dict:
    return {"type": "array", "title": title, "items": {"type": item_type}}


def _datetime(title: str) -> dict:
    return {"type": "string", "format": "date-time", "title": title}


def _date(title: str) -> dict:
    return {"type": "string", "format": "date", "title": title}


def _object(title: str, properties: dict, required: list[str] | None = None) -> dict:
    schema: dict = {
        "type": "object",
        "title": title,
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _time(title: str) -> dict:
    return {"type": "string", "format": "time", "title": title}


def _integer(title: str, minimum: int = 0) -> dict:
    return {"type": "integer", "title": title, "minimum": minimum}


def _member_ids(title: str, widget: str, format_name: str) -> dict:
    return {
        "type": "array",
        "title": title,
        "items": {"type": "string"},
        "uniqueItems": True,
        "format": format_name,
        "x-widget": widget,
    }


def _member_multiselect(title: str) -> dict:
    return _member_ids(title, "member-multiselect", "member-ids")


def _children_visited(title: str = "Children visited") -> dict:
    return _member_ids(title, "child-multiselect", "child-ids")


DRILL_REQUIRED = (
    "date",
    "start_time",
    "end_time",
    "evacuation_seconds",
    "participants",
)
DRILL_EXPORT_PATHS = (
    "payload.date",
    "payload.start_time",
    "payload.end_time",
    "payload.evacuation_seconds",
    "payload.participants",
    "payload.notes",
    "log.occurred_at",
    "log.recorded_by",
)


def _emergency_drill_schema(title: str, extra: dict | None = None) -> dict:
    properties = {
        "date": _date("Date"),
        "start_time": _time("Start time"),
        "end_time": _time("End time"),
        "evacuation_seconds": _integer("Seconds to evacuate"),
        "participants": _member_multiselect("Members participating"),
        **(extra or {}),
        "notes": _string("Notes"),
    }
    return _object(title, properties, list(DRILL_REQUIRED))


FIRE_DRILL = FormType(
    code="fire_drill",
    name="Fire Drill",
    category="household",
    scope="household",
    description="Record a household fire drill with timing and who participated.",
    schema=_emergency_drill_schema(
        "Fire Drill",
        {
            "alarm_tested": _bool("Smoke/fire alarm tested"),
            "meeting_point": _string("Meeting point"),
            "issues_found": _string("Issues found"),
        },
    ),
    export_paths=DRILL_EXPORT_PATHS
    + ("payload.alarm_tested", "payload.meeting_point", "payload.issues_found"),
)

TORNADO_DRILL = FormType(
    code="tornado_drill",
    name="Tornado / Severe Weather Drill",
    category="household",
    scope="household",
    description="Severe weather shelter drill with timing and who participated.",
    schema=_emergency_drill_schema(
        "Tornado Drill",
        {
            "shelter_location": _string("Shelter location"),
            "weather_radio_tested": _bool("Weather radio / alert tested"),
            "issues_found": _string("Issues found"),
        },
    ),
    export_paths=DRILL_EXPORT_PATHS
    + (
        "payload.shelter_location",
        "payload.weather_radio_tested",
        "payload.issues_found",
    ),
)

EMERGENCY_KIT = FormType(
    code="emergency_kit_check",
    name="Emergency Kit Check",
    category="household",
    scope="household",
    description="Inventory and expiration check of emergency supplies.",
    schema=_object(
        "Emergency Kit Check",
        {
            "kit_location": _string("Kit location"),
            "water_ok": _bool("Water supply current"),
            "food_ok": _bool("Food supply current"),
            "first_aid_ok": _bool("First aid complete"),
            "flashlight_ok": _bool("Flashlight / batteries ok"),
            "documents_ok": _bool("Emergency documents present"),
            "expired_items": _array("Expired items replaced"),
            "notes": _string("Notes"),
        },
        ["kit_location", "water_ok", "food_ok", "first_aid_ok"],
    ),
)

GUEST_VISITOR = FormType(
    code="guest_visitor",
    name="Guest / Visitor",
    category="household",
    scope="household",
    description="Log household guests and overnight visitors.",
    schema=_object(
        "Guest / Visitor",
        {
            "visitor_name": _string("Visitor name"),
            "relationship": _string("Relationship"),
            "purpose": _string("Purpose of visit"),
            "arrived_at": _datetime("Arrived"),
            "departed_at": _datetime("Departed"),
            "overnight": _bool("Overnight stay"),
            "supervised": _bool("Supervised around children"),
            "notes": _string("Notes"),
        },
        ["visitor_name", "purpose", "arrived_at"],
    ),
)

HOME_MAINTENANCE = FormType(
    code="home_maintenance",
    name="Home Maintenance",
    category="household",
    scope="household",
    description="Repairs, safety issues, and completed household maintenance.",
    schema=_object(
        "Home Maintenance",
        {
            "area": _string("Area / room"),
            "issue": _string("Issue"),
            "work_performed": _string("Work performed"),
            "vendor": _string("Vendor / person"),
            "cost": _string("Cost"),
            "safety_related": _bool("Safety related"),
            "follow_up": _string("Follow-up"),
        },
        ["area", "issue", "work_performed"],
    ),
)

HOUSEHOLD_MEETING = FormType(
    code="household_meeting",
    name="Household Meeting",
    category="household",
    scope="household",
    description="Family/household meeting agenda, attendees, and decisions.",
    schema=_object(
        "Household Meeting",
        {
            "attendees": _array("Attendees"),
            "agenda": _string("Agenda"),
            "decisions": _string("Decisions"),
            "chores_assigned": _string("Chores / responsibilities assigned"),
            "next_meeting": _date("Next meeting"),
        },
        ["attendees", "agenda"],
    ),
)

CASE_WORKER_VISIT = FormType(
    code="case_worker_visit",
    name="Case Worker Visit",
    category="foster",
    scope="household",
    description="Document a case worker home or office visit.",
    schema=_object(
        "Case Worker Visit",
        {
            "children_visited": _children_visited(),
            "worker_name": _string("Case worker name"),
            "agency": _string("Agency"),
            "visit_type": {
                "type": "string",
                "title": "Visit type",
                "enum": ["home", "office", "virtual", "school", "other"],
            },
            "announced": _bool("Announced visit"),
            "topics": _string("Topics discussed"),
            "caregiver_present": _bool("Caregiver present"),
            "concerns": _string("Concerns raised"),
            "action_items": _string("Action items"),
            "next_visit": _date("Next visit"),
            "private_time_with_child": _bool("Private time with child"),
        },
        ["children_visited", "worker_name", "visit_type", "topics"],
    ),
)

SIBLING_CONTACT = FormType(
    code="sibling_contact",
    name="Sibling Contact",
    category="foster",
    scope="household",
    description="Record contact between siblings placed in separate homes (CFS-400).",
    schema=_object(
        "Sibling Contact",
        {
            "date": _date("Date"),
            "start_time": _time("Start time"),
            "end_time": _time("End time"),
            "siblings_in_home": _children_visited("Siblings in this home"),
            "other_siblings": _array("Other siblings (not in this home)"),
            "contact_type": {
                "type": "string",
                "title": "Type of contact",
                "enum": [
                    "Face-to-face",
                    "Phone call",
                    "Text",
                    "Video (Skype / FaceTime)",
                    "Other",
                ],
            },
            "notes": _string("Notes"),
        },
        ["date", "start_time", "end_time", "siblings_in_home", "contact_type"],
    ),
)

FAMILY_VISIT = FormType(
    code="family_visit",
    name="Family / Bio Visit",
    category="foster",
    scope="household",
    description="Visitation with biological family or identified connections.",
    schema=_object(
        "Family Visit",
        {
            "children_visited": _children_visited(),
            "visitors": _array("Visitors"),
            "relationship": _string("Relationship"),
            "location": _string("Location"),
            "supervised": _bool("Supervised"),
            "supervisor_name": _string("Supervisor name"),
            "started_at": _datetime("Started"),
            "ended_at": _datetime("Ended"),
            "transport_by": _string("Transported by"),
            "child_response": _string("Child response"),
            "incidents": _string("Incidents"),
            "next_visit": _date("Next visit"),
        },
        [
            "children_visited",
            "visitors",
            "location",
            "started_at",
            "ended_at",
            "supervised",
        ],
    ),
)

COURT_HEARING = FormType(
    code="court_hearing",
    name="Court / Hearing",
    category="foster",
    scope="member",
    description="Court, staffing, or administrative hearing record.",
    schema=_object(
        "Court Hearing",
        {
            "hearing_type": _string("Hearing type"),
            "court": _string("Court / location"),
            "case_number": _string("Case number"),
            "judge": _string("Judge / officer"),
            "attendees": _array("Attendees"),
            "outcome": _string("Outcome / orders"),
            "next_date": _date("Next court date"),
            "child_present": _bool("Child present"),
        },
        ["hearing_type", "court", "outcome"],
    ),
)

GAL_CONTACT = FormType(
    code="gal_casa_contact",
    name="GAL / CASA Contact",
    category="foster",
    scope="member",
    description="Contact with guardian ad litem or CASA volunteer.",
    schema=_object(
        "GAL / CASA Contact",
        {
            "contact_name": _string("Name"),
            "role": {
                "type": "string",
                "title": "Role",
                "enum": ["gal", "casa", "attorney_ad_litem", "other"],
            },
            "method": {
                "type": "string",
                "title": "Method",
                "enum": ["phone", "email", "in_person", "virtual"],
            },
            "summary": _string("Summary"),
            "follow_up": _string("Follow-up"),
        },
        ["contact_name", "role", "method", "summary"],
    ),
)

RESPITE = FormType(
    code="respite",
    name="Respite",
    category="foster",
    scope="member",
    description="Respite care start/end, provider, and child adjustment.",
    schema=_object(
        "Respite",
        {
            "provider_name": _string("Respite provider"),
            "provider_phone": _string("Provider phone"),
            "started_at": _datetime("Started"),
            "ended_at": _datetime("Ended"),
            "medications_sent": _bool("Medications sent"),
            "supplies_sent": _string("Supplies sent"),
            "child_adjustment": _string("Child adjustment"),
            "incidents": _string("Incidents"),
        },
        ["provider_name", "started_at"],
    ),
)

INCIDENT = FormType(
    code="incident",
    name="Incident",
    category="foster",
    scope="member",
    description="Safety or significant incident requiring documentation.",
    schema=_object(
        "Incident",
        {
            "severity": {
                "type": "string",
                "title": "Severity",
                "enum": ["low", "moderate", "high", "critical"],
            },
            "location": _string("Location"),
            "what_happened": _string("What happened"),
            "people_involved": _array("People involved"),
            "injury": _bool("Injury"),
            "injury_details": _string("Injury details"),
            "first_aid": _string("First aid / medical care"),
            "notified": _array("People/agencies notified"),
            "notified_at": _datetime("Notified at"),
            "follow_up": _string("Follow-up"),
        },
        ["severity", "location", "what_happened"],
    ),
)

RPP = FormType(
    code="reasonable_prudent_parenting",
    name="Reasonable and Prudent Parenting",
    category="foster",
    scope="member",
    description="Normalcy activities approved under reasonable and prudent parenting.",
    schema=_object(
        "Reasonable and Prudent Parenting",
        {
            "activity": _string("Activity"),
            "location": _string("Location"),
            "supervision": _string("Supervision plan"),
            "risks_considered": _string("Risks considered"),
            "decision": {
                "type": "string",
                "title": "Decision",
                "enum": ["approved", "denied", "modified"],
            },
            "transportation": _string("Transportation"),
            "overnight": _bool("Overnight"),
            "notes": _string("Notes"),
        },
        ["activity", "decision", "risks_considered"],
    ),
)

ALLOWANCE = FormType(
    code="allowance_clothing",
    name="Allowance / Clothing",
    category="foster",
    scope="member",
    description="Allowance disbursement or clothing purchase for a child.",
    schema=_object(
        "Allowance / Clothing",
        {
            "kind": {
                "type": "string",
                "title": "Kind",
                "enum": ["allowance", "clothing", "personal_needs", "gift"],
            },
            "amount": _string("Amount"),
            "items": _string("Items / description"),
            "store": _string("Store / source"),
            "receipt_kept": _bool("Receipt kept"),
            "child_involved": _bool("Child helped choose"),
        },
        ["kind", "amount", "items"],
    ),
)

LIFE_SKILLS = FormType(
    code="life_skills",
    name="Life Skills",
    category="foster",
    scope="member",
    description="Independent living or life-skills practice.",
    schema=_object(
        "Life Skills",
        {
            "skill": _string("Skill practiced"),
            "setting": _string("Setting"),
            "support_given": _string("Support given"),
            "child_response": _string("Child response"),
            "next_step": _string("Next step"),
        },
        ["skill", "support_given"],
    ),
)

PSYCHOTROPIC_REVIEW = FormType(
    code="psychotropic_med_review",
    name="Psychotropic Medication Review",
    category="foster",
    scope="member",
    description="Consent, monitoring, and review of psychotropic medication.",
    schema=_object(
        "Psychotropic Medication Review",
        {
            "medication_name": _string("Medication"),
            "reviewer": _string("Reviewer (clinician / court / worker)"),
            "consent_on_file": _bool("Informed consent on file"),
            "side_effects": _string("Side effects observed"),
            "effectiveness": _string("Effectiveness"),
            "labs_due": _date("Labs due"),
            "decision": _string("Decision / changes"),
        },
        ["medication_name", "reviewer", "consent_on_file"],
    ),
)

DAILY_CARE = FormType(
    code="daily_care",
    name="Daily Care Log",
    category="caregiving",
    scope="member",
    description="Meals, hygiene, mood, activities, homework, and sleep.",
    schema=_object(
        "Daily Care Log",
        {
            "breakfast": _string("Breakfast"),
            "lunch": _string("Lunch"),
            "dinner": _string("Dinner"),
            "snacks": _string("Snacks"),
            "appetite": {
                "type": "string",
                "title": "Appetite",
                "enum": ["poor", "fair", "good", "excellent"],
            },
            "hygiene": _string("Hygiene / self-care"),
            "mood": _string("Mood / behavior"),
            "activities": _string("Activities"),
            "homework": _string("Homework / schoolwork"),
            "bedtime": _string("Bedtime"),
            "sleep_quality": {
                "type": "string",
                "title": "Sleep quality",
                "enum": ["poor", "fair", "good", "restless", "nightmares"],
            },
            "health_notes": _string("Health notes"),
            "notes": _string("Additional notes"),
        },
        ["mood", "activities"],
    ),
)

MEDICATION_ADMIN = FormType(
    code="medication_administration",
    name="Medication Administration",
    category="caregiving",
    scope="member",
    description="Give a medication from the member profile (MAR).",
    schema=_object(
        "Medication Administration",
        {
            "medication_id": _string("Medication id"),
            "medication_name": _string("Medication name"),
            "dose_given": _string("Dose given"),
            "quantity_given": _integer("Number given", minimum=1),
            "route": _string("Route"),
            "outcome": {
                "type": "string",
                "title": "Outcome",
                "enum": ["given", "refused", "missed", "held"],
            },
            "held_reason": _string("Held / missed / refused reason"),
            "fp_initials": _string("Foster parent initials"),
            "fc_initials": _string("Child initials"),
            "notes": _string("Notes"),
        },
        ["medication_id", "medication_name", "dose_given", "quantity_given", "outcome"],
    ),
)

APPOINTMENT = FormType(
    code="appointment",
    name="Medical / Dental / Therapy Appointment",
    category="caregiving",
    scope="member",
    description="Health appointment, findings, and follow-up.",
    schema=_object(
        "Appointment",
        {
            "kind": {
                "type": "string",
                "title": "Kind",
                "enum": [
                    "medical",
                    "dental",
                    "therapy",
                    "psychiatry",
                    "vision",
                    "specialty",
                    "other",
                ],
            },
            "provider": _string("Provider"),
            "location": _string("Location"),
            "reason": _string("Reason"),
            "findings": _string("Findings"),
            "follow_up": _string("Follow-up instructions"),
            "next_appointment": _date("Next appointment"),
            "missed": _bool("Missed / no-show"),
        },
        ["kind", "provider", "reason"],
    ),
)

IMMUNIZATION = FormType(
    code="immunization",
    name="Immunization",
    category="caregiving",
    scope="member",
    description="Vaccine administration record.",
    schema=_object(
        "Immunization",
        {
            "vaccine": _string("Vaccine"),
            "dose_number": _string("Dose number"),
            "lot": _string("Lot number"),
            "site": _string("Site"),
            "administered_by": _string("Administered by"),
            "location": _string("Clinic / location"),
            "reaction": _string("Reaction"),
            "next_due": _date("Next due"),
        },
        ["vaccine", "administered_by"],
    ),
)

TRANSPORTATION = FormType(
    code="transportation",
    name="Transportation",
    category="caregiving",
    scope="member",
    description="Transport to school, visits, appointments, or activities.",
    schema=_object(
        "Transportation",
        {
            "purpose": _string("Purpose"),
            "from_location": _string("From"),
            "to_location": _string("To"),
            "driver": _string("Driver"),
            "started_at": _datetime("Departed"),
            "ended_at": _datetime("Arrived"),
            "mileage": _string("Mileage"),
            "notes": _string("Notes"),
        },
        ["purpose", "from_location", "to_location", "driver"],
    ),
)

CHORE = FormType(
    code="chore_responsibility",
    name="Chore / Responsibility",
    category="caregiving",
    scope="member",
    description="Assigned chores and how they were completed.",
    schema=_object(
        "Chore / Responsibility",
        {
            "chore": _string("Chore"),
            "completed": _bool("Completed"),
            "quality": {
                "type": "string",
                "title": "Quality",
                "enum": ["needs_help", "adequate", "good", "excellent"],
            },
            "support_given": _string("Support given"),
            "notes": _string("Notes"),
        },
        ["chore", "completed"],
    ),
)

FORM_TYPES: tuple[FormType, ...] = (
    FIRE_DRILL,
    TORNADO_DRILL,
    EMERGENCY_KIT,
    GUEST_VISITOR,
    HOME_MAINTENANCE,
    HOUSEHOLD_MEETING,
    CASE_WORKER_VISIT,
    SIBLING_CONTACT,
    FAMILY_VISIT,
    COURT_HEARING,
    GAL_CONTACT,
    RESPITE,
    INCIDENT,
    RPP,
    ALLOWANCE,
    LIFE_SKILLS,
    PSYCHOTROPIC_REVIEW,
    DAILY_CARE,
    MEDICATION_ADMIN,
    APPOINTMENT,
    IMMUNIZATION,
    TRANSPORTATION,
    CHORE,
)

_BY_CODE = {item.code: item for item in FORM_TYPES}


def get_form_type(code: str) -> FormType:
    try:
        return _BY_CODE[code]
    except KeyError as exc:
        raise DomainError(f"Unknown form type: {code}") from exc
