from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import household_service, otc_service, require_scopes
from app.core.auth.scopes import (
    DISCIPLINE_READ,
    DISCIPLINE_WRITE,
    DOCUMENTS_READ,
    DOCUMENTS_WRITE,
    EDUCATION_READ,
    EDUCATION_WRITE,
    LOGS_AMEND,
    LOGS_EXPORT,
    LOGS_READ,
    LOGS_WRITE,
    MEMBERS_INVITE,
    MEMBERS_MANAGE,
    MEMBERS_READ,
    PROFILES_READ,
    PROFILES_WRITE,
)
from app.core.auth.user import AuthUser
from app.core.errors import DomainError
from app.db.session import get_db
from app.exports.service import OfficialExportService
from app.permissions.service import PermissionService
from app.schemas import (
    AllergyIn,
    ClinicianIn,
    DiagnosisIn,
    DisabilityIn,
    DisciplineIn,
    EmergencyContactIn,
    EnrollmentIn,
    FormExportRequest,
    GradeIn,
    HouseholdOtcMedicationIn,
    HouseholdOtcMedicationUpdate,
    LogAmend,
    LogCreate,
    MedicationIn,
    MedicationUpdate,
    MemberCreate,
    MemberOtcAssignmentIn,
    MemberStatusUpdate,
    MemberUpdate,
    PermissionReplace,
    ProfessionalContactIn,
    ProfileUpdate,
)
from app.services.households import HouseholdService, ProfileService
from app.services.operations import (
    DashboardService,
    DisciplineService,
    DocumentService,
    EducationService,
    ExportService,
    LogService,
    serialize_log,
    serialize_medication,
    serialize_member,
    serialize_profile,
)
from app.services.otc import OtcService, serialize_assignment, serialize_otc
from app.storage.files import LocalFileStore
from app.storage.images import IMAGE_EXTENSIONS, sniff_image_media_type

members_router = APIRouter()
logs_router = APIRouter()
more_router = APIRouter()


@members_router.get("/households/{household_id}/members")
def list_members(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    include_inactive: bool = False,
) -> list[dict]:
    service.require_membership(household_id, user)
    return [
        serialize_member(item)
        for item in service.list_members(
            household_id, include_inactive=include_inactive
        )
    ]


@members_router.post("/households/{household_id}/members", status_code=201)
def add_member(
    household_id: str,
    data: MemberCreate,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(service.db).require(household_id, user, "tab.people", "add")
    return serialize_member(service.add_member(household_id, data, user))


@members_router.get("/households/{household_id}/members/{member_id}")
def get_member(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_member(service.get_member(household_id, member_id))


@members_router.get("/households/{household_id}/members/{member_id}/permissions")
def list_member_permissions(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    service.require_membership(household_id, user)
    return PermissionService(db).list_for_member(household_id, member_id)


@members_router.put("/households/{household_id}/members/{member_id}/permissions")
def replace_member_permissions(
    household_id: str,
    member_id: str,
    data: PermissionReplace,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    service.require_membership(household_id, user)
    return PermissionService(db).replace_for_member(
        household_id, member_id, data.grants, user
    )


@members_router.patch("/households/{household_id}/members/{member_id}")
def update_member(
    household_id: str,
    member_id: str,
    data: MemberUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(service.db).require(household_id, user, "tab.people", "edit")
    return serialize_member(service.update_member(household_id, member_id, data, user))


@members_router.post("/households/{household_id}/members/{member_id}/invite")
def invite_member(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_INVITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_member(service.invite(household_id, member_id, user))


@members_router.post("/households/{household_id}/members/{member_id}/deactivate")
def deactivate_member(
    household_id: str,
    member_id: str,
    data: MemberStatusUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_member(service.deactivate(household_id, member_id, data, user))


@members_router.post("/households/{household_id}/members/{member_id}/activate")
def activate_member(
    household_id: str,
    member_id: str,
    data: MemberStatusUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(MEMBERS_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_member(service.activate(household_id, member_id, data, user))


@members_router.get("/households/{household_id}/members/{member_id}/profile")
def get_profile(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    profile = ProfileService(db).get_profile(household_id, member_id)
    return serialize_profile(profile)


@members_router.patch("/households/{household_id}/members/{member_id}/profile")
def update_profile(
    household_id: str,
    member_id: str,
    data: ProfileUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    profile = ProfileService(db).update_profile(household_id, member_id, data, user)
    return serialize_profile(profile)


@members_router.get("/households/{household_id}/otc-medications")
def list_otc_medications(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> list[dict]:
    service.require_membership(household_id, user)
    return [serialize_otc(item) for item in otc.list_catalog(household_id)]


@members_router.post("/households/{household_id}/otc-medications", status_code=201)
def add_otc_medication(
    household_id: str,
    data: HouseholdOtcMedicationIn,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_otc(otc.add_catalog(household_id, data, user))


@members_router.patch("/households/{household_id}/otc-medications/{otc_id}")
def update_otc_medication(
    household_id: str,
    otc_id: str,
    data: HouseholdOtcMedicationUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_otc(otc.update_catalog(household_id, otc_id, data, user))


@members_router.delete(
    "/households/{household_id}/otc-medications/{otc_id}", status_code=204
)
def delete_otc_medication(
    household_id: str,
    otc_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> None:
    service.require_membership(household_id, user)
    otc.delete_catalog(household_id, otc_id, user)


@members_router.post(
    "/households/{household_id}/members/{member_id}/otc-medications", status_code=201
)
def assign_otc_medication(
    household_id: str,
    member_id: str,
    data: MemberOtcAssignmentIn,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> dict:
    service.require_membership(household_id, user)
    return serialize_assignment(otc.assign(household_id, member_id, data, user))


@members_router.delete(
    "/households/{household_id}/members/{member_id}/otc-medications/{assignment_id}",
    status_code=204,
)
def unassign_otc_medication(
    household_id: str,
    member_id: str,
    assignment_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    otc: Annotated[OtcService, Depends(otc_service)],
) -> None:
    service.require_membership(household_id, user)
    otc.unassign(household_id, member_id, assignment_id, user)


NESTED_MODELS = {
    "allergies": AllergyIn,
    "medications": MedicationIn,
    "diagnoses": DiagnosisIn,
    "disabilities": DisabilityIn,
    "clinicians": ClinicianIn,
    "professional_contacts": ProfessionalContactIn,
    "emergency_contacts": EmergencyContactIn,
}


@members_router.post("/households/{household_id}/members/{member_id}/photo")
async def upload_photo(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> dict:
    service.require_membership(household_id, user)
    data = await file.read()
    media_type = sniff_image_media_type(data)
    path = LocalFileStore().save(
        household_id,
        f"photos/{member_id}",
        f"portrait{IMAGE_EXTENSIONS[media_type]}",
        data,
    )
    profile = ProfileService(db).set_photo(household_id, member_id, path, user)
    return serialize_profile(profile)


@members_router.get("/households/{household_id}/members/{member_id}/photo")
def get_photo(
    household_id: str,
    member_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    service.require_membership(household_id, user)
    profile = ProfileService(db).get_profile(household_id, member_id)
    if not profile.photo_path:
        raise DomainError("Photo not found", 404)
    try:
        data = LocalFileStore().read(profile.photo_path)
    except FileNotFoundError as exc:
        raise DomainError("Photo not found", 404) from exc
    return Response(content=data, media_type=sniff_image_media_type(data))


@members_router.post("/households/{household_id}/members/{member_id}/{collection}")
def add_nested(
    household_id: str,
    member_id: str,
    collection: str,
    payload: dict,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    model = NESTED_MODELS.get(collection)
    if model is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Unknown collection")
    item = ProfileService(db).add_nested(
        household_id, member_id, collection, model.model_validate(payload), user
    )
    return {"id": item.id}


@members_router.patch(
    "/households/{household_id}/members/{member_id}/{collection}/{item_id}"
)
def update_nested(
    household_id: str,
    member_id: str,
    collection: str,
    item_id: str,
    payload: dict,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    if collection != "medications":
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Unknown collection")
    item = ProfileService(db).update_nested(
        household_id,
        member_id,
        collection,
        item_id,
        MedicationUpdate.model_validate(payload),
        user,
    )
    return serialize_medication(item)


@members_router.delete(
    "/households/{household_id}/members/{member_id}/{collection}/{item_id}",
    status_code=204,
)
def delete_nested(
    household_id: str,
    member_id: str,
    collection: str,
    item_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(PROFILES_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    service.require_membership(household_id, user)
    ProfileService(db).delete_nested(household_id, member_id, collection, item_id, user)


@logs_router.get("/form-types")
def form_types(
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_READ))],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return LogService(db).list_types()


@logs_router.get("/export-forms")
def export_forms(
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_EXPORT))],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return OfficialExportService(db).list_forms()


@logs_router.post("/households/{household_id}/form-exports")
def create_form_export(
    household_id: str,
    data: FormExportRequest,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_EXPORT))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    service.require_membership(household_id, user)
    PermissionService(db).require_export(household_id, user, data.form_code)
    content = OfficialExportService(db).export_pdf(
        household_id,
        data.form_code,
        data.start_date,
        data.end_date,
        data.member_ids,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=form-export.pdf"},
    )


@logs_router.post("/households/{household_id}/logs", status_code=201)
def create_log(
    household_id: str,
    data: LogCreate,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    recorder = service.require_membership(household_id, user)
    PermissionService(db).require_form(household_id, user, data.form_type_code, "add")
    entry = LogService(db).create(household_id, data, user, recorder)
    return serialize_log(entry, db)


@logs_router.get("/households/{household_id}/logs")
def list_logs(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    form_type_code: str | None = None,
    member_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.logs", "view")
    perms = PermissionService(db)
    entries = LogService(db).list_logs(
        household_id,
        form_type_code=form_type_code,
        member_id=member_id,
        status=status,
    )
    return [
        serialize_log(entry, db)
        for entry in entries
        if perms.can(household_id, user, f"form.{entry.form_type_code}", "view")
    ]


@logs_router.get("/households/{household_id}/logs-export")
def export_logs(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_EXPORT))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("pdf"),
    form_type_code: str | None = None,
    member_id: str | None = None,
) -> Response:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.export", "view")
    household = service.get(household_id)
    entries = LogService(db).list_logs(
        household_id, form_type_code=form_type_code, member_id=member_id
    )
    exporter = ExportService(db)
    if format == "csv":
        return Response(
            content=exporter.csv_bytes(household_id, entries),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=home-logs.csv"},
        )
    return Response(
        content=exporter.branded_pdf(household.name, entries),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=home-logs.pdf"},
    )


@logs_router.get("/households/{household_id}/logs/{log_id}")
def get_log(
    household_id: str,
    log_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    entry = LogService(db).get(household_id, log_id)
    PermissionService(db).require_form(household_id, user, entry.form_type_code, "view")
    return serialize_log(entry, db)


@logs_router.patch("/households/{household_id}/logs/{log_id}")
def update_log(
    household_id: str,
    log_id: str,
    data: LogCreate,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require_form(household_id, user, data.form_type_code, "edit")
    return serialize_log(
        LogService(db).update_draft(household_id, log_id, data, user), db
    )


@logs_router.post("/households/{household_id}/logs/{log_id}/submit")
def submit_log(
    household_id: str,
    log_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    entry = LogService(db).get(household_id, log_id)
    PermissionService(db).require_form(household_id, user, entry.form_type_code, "edit")
    return serialize_log(LogService(db).submit(household_id, log_id, user), db)


@logs_router.post("/households/{household_id}/logs/{log_id}/amend")
def amend_log(
    household_id: str,
    log_id: str,
    data: LogAmend,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_AMEND))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    recorder = service.require_membership(household_id, user)
    entry = LogService(db).get(household_id, log_id)
    PermissionService(db).require_form(household_id, user, entry.form_type_code, "edit")
    return serialize_log(
        LogService(db).amend(household_id, log_id, data, user, recorder), db
    )


@more_router.get("/households/{household_id}/dashboard")
def dashboard(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(LOGS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.dashboard", "view")
    return DashboardService(db).snapshot(household_id)


@more_router.post("/households/{household_id}/discipline", status_code=201)
def create_discipline(
    household_id: str,
    data: DisciplineIn,
    user: Annotated[AuthUser, Depends(require_scopes(DISCIPLINE_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    recorder = service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.discipline", "add")
    record = DisciplineService(db).create(household_id, data, user, recorder)
    return {"id": record.id, "log_entry_id": record.log_entry_id}


@more_router.get("/households/{household_id}/discipline")
def list_discipline(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(DISCIPLINE_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    member_id: str | None = None,
) -> list[dict]:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.discipline", "view")
    records = DisciplineService(db).list(household_id, member_id)
    return [
        {
            "id": item.id,
            "member_id": item.member_id,
            "occurred_at": item.occurred_at.isoformat(),
            "location": item.location,
            "antecedent": item.antecedent,
            "behavior": item.behavior,
            "intervention": item.intervention,
            "consequence": item.consequence,
            "duration_minutes": item.duration_minutes,
            "follow_up": item.follow_up,
            "notified": item.notified,
            "log_entry_id": item.log_entry_id,
        }
        for item in records
    ]


@more_router.post("/households/{household_id}/enrollments", status_code=201)
def add_enrollment(
    household_id: str,
    data: EnrollmentIn,
    user: Annotated[AuthUser, Depends(require_scopes(EDUCATION_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.school", "add")
    enrollment = EducationService(db).add_enrollment(household_id, data, user)
    return {"id": enrollment.id}


@more_router.get("/households/{household_id}/enrollments")
def list_enrollments(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(EDUCATION_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    member_id: str | None = None,
) -> list[dict]:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.school", "view")
    rows = EducationService(db).list_enrollments(household_id, member_id)
    return [
        {
            "id": item.id,
            "member_id": item.member_id,
            "school_name": item.school_name,
            "campus": item.campus,
            "grade_level": item.grade_level,
            "school_year": item.school_year,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
            "iep": item.iep,
            "plan_504": item.plan_504,
            "counselor": item.counselor,
            "teacher": item.teacher,
            "grades": [
                {
                    "id": grade.id,
                    "term": grade.term,
                    "course": grade.course,
                    "letter": grade.letter,
                    "percent": grade.percent,
                    "comments": grade.comments,
                }
                for grade in item.grades
            ],
            "report_cards": [
                {
                    "id": card.id,
                    "term": card.term,
                    "filename": card.filename,
                    "issued_on": card.issued_on.isoformat() if card.issued_on else None,
                    "notes": card.notes,
                }
                for card in item.report_cards
            ],
        }
        for item in rows
    ]


@more_router.post("/households/{household_id}/enrollments/{enrollment_id}/grades")
def add_grade(
    household_id: str,
    enrollment_id: str,
    data: GradeIn,
    user: Annotated[AuthUser, Depends(require_scopes(EDUCATION_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.school", "edit")
    grade = EducationService(db).add_grade(household_id, enrollment_id, data, user)
    return {"id": grade.id}


@more_router.post("/households/{household_id}/enrollments/{enrollment_id}/report-cards")
async def add_report_card(
    household_id: str,
    enrollment_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(EDUCATION_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    term: str = Form(...),
    notes: str | None = Form(None),
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.school", "edit")
    data = await file.read()
    card = EducationService(db).add_report_card(
        household_id,
        enrollment_id,
        term=term,
        filename=file.filename or "report-card.pdf",
        data=data,
        actor=user,
        notes=notes,
    )
    return {"id": card.id}


@more_router.post("/households/{household_id}/documents", status_code=201)
async def add_document(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(DOCUMENTS_WRITE))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    member_id: str | None = Form(None),
    notes: str | None = Form(None),
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.documents", "add")
    data = await file.read()
    doc = DocumentService(db).create(
        household_id,
        member_id=member_id,
        category=category,
        title=title,
        filename=file.filename or "file.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        notes=notes,
        actor=user,
    )
    return {"id": doc.id}


@more_router.get("/households/{household_id}/documents")
def list_documents(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(DOCUMENTS_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
    member_id: str | None = None,
) -> list[dict]:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.documents", "view")
    return [
        {
            "id": item.id,
            "member_id": item.member_id,
            "category": item.category,
            "title": item.title,
            "filename": item.filename,
            "content_type": item.content_type,
            "notes": item.notes,
            "created_at": item.created_at.isoformat(),
        }
        for item in DocumentService(db).list(household_id, member_id)
    ]
