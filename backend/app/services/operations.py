from __future__ import annotations

import csv
from contextlib import suppress
from datetime import UTC, date, datetime
from io import BytesIO, StringIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.forms.catalog import FORM_TYPES, get_form_type
from app.forms.validate import normalize_payload, validate_payload
from app.models import (
    CourseGrade,
    DisciplineRecord,
    Document,
    Household,
    HouseholdMember,
    LogAttachment,
    LogEntry,
    Medication,
    PdfPlaceholder,
    PdfTemplate,
    PersonProfile,
    ReportCard,
    SchoolEnrollment,
)
from app.schemas import DisciplineIn, EnrollmentIn, GradeIn, LogAmend, LogCreate
from app.services.dose import administered_dose
from app.services.households import HouseholdService, audit, legal_name
from app.services.med_rules import is_administerable
from app.services.otc import resolve_administered_medication, serialize_assignment
from app.services.timezones import (
    iso_utc,
    local_date,
    range_end_utc,
    range_start_utc,
    to_utc_naive,
)
from app.storage.files import LocalFileStore


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _household_tz(db: Session, household_id: str) -> str:
    household = db.get(Household, household_id)
    return household.timezone if household and household.timezone else "America/Chicago"


class LogService:
    def __init__(self, db: Session, files: LocalFileStore | None = None) -> None:
        self.db = db
        self.households = HouseholdService(db)
        self.files = files or LocalFileStore()

    def list_types(self) -> list[dict]:
        return [
            {
                "code": item.code,
                "name": item.name,
                "category": item.category,
                "scope": item.scope,
                "description": item.description,
                "schema": item.schema,
            }
            for item in FORM_TYPES
        ]

    def create(
        self, household_id: str, data: LogCreate, actor, recorder: HouseholdMember
    ) -> LogEntry:
        form = get_form_type(data.form_type_code)
        if form.scope == "member" and not data.subject_member_id:
            raise DomainError("This form requires a household member")
        payload = normalize_payload(form.schema, dict(data.payload))
        if data.subject_member_id:
            self.households.get_member(household_id, data.subject_member_id)
        self._validate(
            form.code,
            household_id,
            data.subject_member_id,
            payload,
            occurred_at=data.occurred_at,
        )
        errors = validate_payload(form.schema, payload)
        if errors:
            raise DomainError("; ".join(errors))
        entry = LogEntry(
            household_id=household_id,
            form_type_code=form.code,
            subject_member_id=data.subject_member_id,
            recorded_by_id=recorder.id,
            occurred_at=to_utc_naive(data.occurred_at),
            status="submitted" if data.submit else "draft",
            payload=payload,
        )
        self.db.add(entry)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="log",
            entity_id=entry.id,
            summary=f"Created {form.name} log",
        )
        return entry

    def _validate(
        self,
        code: str,
        household_id: str,
        member_id: str | None,
        payload: dict,
        occurred_at: datetime | None = None,
    ) -> None:
        if code != "medication_administration":
            return
        if not member_id:
            raise DomainError("Medication log requires a member")
        member = self.households.get_member(household_id, member_id)
        on = (
            local_date(occurred_at, _household_tz(self.db, household_id))
            if occurred_at
            else date.today()
        )
        name, dose, route, _psychotropic = resolve_administered_medication(
            self.db,
            household_id,
            member.profile,
            payload.get("medication_id"),
            on=on,
        )
        payload["medication_name"] = name
        quantity = payload.get("quantity_given")
        if quantity not in (None, ""):
            payload["dose_given"] = administered_dose(dose, quantity)
        elif not payload.get("dose_given"):
            payload["dose_given"] = dose
        if not payload.get("route"):
            payload["route"] = route

    def list_logs(
        self,
        household_id: str,
        *,
        form_type_code: str | None = None,
        form_type_codes: tuple[str, ...] | list[str] | None = None,
        member_id: str | None = None,
        status: str | None = None,
        occurred_from: date | datetime | None = None,
        occurred_to: date | datetime | None = None,
    ) -> list[LogEntry]:
        stmt = select(LogEntry).where(LogEntry.household_id == household_id)
        if form_type_codes:
            stmt = stmt.where(LogEntry.form_type_code.in_(form_type_codes))
        elif form_type_code:
            stmt = stmt.where(LogEntry.form_type_code == form_type_code)
        if member_id:
            stmt = stmt.where(LogEntry.subject_member_id == member_id)
        if status:
            stmt = stmt.where(LogEntry.status == status)
        tz_name = _household_tz(self.db, household_id)
        start = range_start_utc(occurred_from, tz_name)
        if start is not None:
            stmt = stmt.where(LogEntry.occurred_at >= start)
        end = range_end_utc(occurred_to, tz_name)
        if end is not None:
            stmt = stmt.where(LogEntry.occurred_at < end)
        stmt = stmt.order_by(LogEntry.occurred_at.desc())
        return list(self.db.scalars(stmt))

    def get(self, household_id: str, log_id: str) -> LogEntry:
        entry = self.db.get(LogEntry, log_id)
        if entry is None or entry.household_id != household_id:
            raise DomainError("Log not found", 404)
        return entry

    def update_draft(
        self, household_id: str, log_id: str, data: LogCreate, actor
    ) -> LogEntry:
        entry = self.get(household_id, log_id)
        if entry.status != "draft":
            raise DomainError("Only drafts can be edited")
        form = get_form_type(data.form_type_code or entry.form_type_code)
        payload = normalize_payload(form.schema, dict(data.payload))
        self._validate(
            form.code,
            household_id,
            data.subject_member_id or entry.subject_member_id,
            payload,
            occurred_at=data.occurred_at or entry.occurred_at,
        )
        errors = validate_payload(form.schema, payload)
        if errors:
            raise DomainError("; ".join(errors))
        entry.payload = payload
        entry.form_type_code = form.code
        if data.occurred_at:
            entry.occurred_at = to_utc_naive(data.occurred_at)
        if data.subject_member_id:
            entry.subject_member_id = data.subject_member_id
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="log",
            entity_id=entry.id,
            summary="Updated draft log",
        )
        return entry

    def submit(self, household_id: str, log_id: str, actor) -> LogEntry:
        entry = self.get(household_id, log_id)
        entry.status = "submitted"
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="submit",
            entity_type="log",
            entity_id=entry.id,
            summary="Submitted log",
        )
        return entry

    def amend(
        self, household_id: str, log_id: str, data: LogAmend, actor, recorder
    ) -> LogEntry:
        original = self.get(household_id, log_id)
        if original.status == "draft":
            raise DomainError("Submit the draft before amending")
        form = get_form_type(original.form_type_code)
        payload = normalize_payload(form.schema, dict(data.payload))
        payload["amendment_reason"] = data.reason
        self._validate(
            form.code,
            household_id,
            original.subject_member_id,
            payload,
            occurred_at=data.occurred_at or original.occurred_at,
        )
        errors = validate_payload(form.schema, payload)
        # amendment_reason is extra; allow by validating without it
        payload_for_schema = {
            k: v for k, v in payload.items() if k != "amendment_reason"
        }
        errors = validate_payload(form.schema, payload_for_schema)
        if errors:
            raise DomainError("; ".join(errors))
        original.status = "amended"
        entry = LogEntry(
            household_id=household_id,
            form_type_code=original.form_type_code,
            subject_member_id=original.subject_member_id,
            recorded_by_id=recorder.id,
            occurred_at=(
                to_utc_naive(data.occurred_at)
                if data.occurred_at
                else original.occurred_at
            ),
            status="submitted",
            payload=payload,
            amended_from_id=original.id,
        )
        self.db.add(entry)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="amend",
            entity_type="log",
            entity_id=entry.id,
            summary=f"Amended log {original.id}",
        )
        return entry

    def attach(
        self,
        household_id: str,
        log_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> LogAttachment:
        entry = self.get(household_id, log_id)
        path = self.files.save(household_id, f"logs/{log_id}", filename, data)
        attachment = LogAttachment(
            log_entry_id=entry.id,
            filename=filename,
            content_type=content_type,
            storage_path=path,
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.logs = LogService(db)

    def csv_bytes(self, household_id: str, entries: list[LogEntry]) -> bytes:
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "form",
                "status",
                "occurred_at",
                "member",
                "payload",
            ]
        )
        for entry in entries:
            member_name = ""
            if entry.subject_member_id:
                member = self.db.get(HouseholdMember, entry.subject_member_id)
                member_name = legal_name(member.profile) if member else ""
            writer.writerow(
                [
                    entry.id,
                    entry.form_type_code,
                    entry.status,
                    entry.occurred_at.isoformat(),
                    member_name,
                    entry.payload,
                ]
            )
        return buffer.getvalue().encode("utf-8")

    def branded_pdf(self, household_name: str, entries: list[LogEntry]) -> bytes:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 48
        pdf.setFillColorRGB(0.043, 0.239, 0.290)
        pdf.rect(0, height - 36, width, 36, fill=1, stroke=0)
        pdf.setFillColorRGB(0.965, 0.945, 0.910)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(24, height - 24, f"Home Logs — {household_name}")
        pdf.setFillColorRGB(0.102, 0.122, 0.141)
        pdf.setFont("Helvetica", 10)
        y = height - 60
        if not entries:
            pdf.drawString(24, y, "No log entries in this range.")
        for entry in entries:
            form = get_form_type(entry.form_type_code)
            member_name = ""
            if entry.subject_member_id:
                member = self.db.get(HouseholdMember, entry.subject_member_id)
                member_name = legal_name(member.profile) if member else ""
            stamp = entry.occurred_at.isoformat(sep=" ", timespec="minutes")
            line = f"{stamp}  {form.name}  {member_name}  [{entry.status}]"
            pdf.drawString(24, y, line[:110])
            y -= 14
            for key, value in entry.payload.items():
                text = f"    {key}: {value}"
                pdf.drawString(24, y, text[:110])
                y -= 12
                if y < 48:
                    pdf.showPage()
                    y = height - 48
            y -= 8
            if y < 48:
                pdf.showPage()
                y = height - 48
        pdf.save()
        return buffer.getvalue()


class PdfTemplateService:
    def __init__(self, db: Session, files: LocalFileStore | None = None) -> None:
        self.db = db
        self.files = files or LocalFileStore()

    def create(
        self,
        household_id: str,
        name: str,
        form_type_code: str,
        filename: str,
        data: bytes,
        actor,
    ):
        name = name.strip()
        if not name:
            raise DomainError("Template name is required")
        get_form_type(form_type_code)
        if not data.startswith(b"%PDF"):
            raise DomainError("File must be a PDF")
        path = self.files.save(household_id, "templates", filename, data)
        template = PdfTemplate(
            household_id=household_id,
            name=name,
            form_type_code=form_type_code,
            storage_path=path,
        )
        self.db.add(template)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="pdf_template",
            entity_id=template.id,
            summary=f"Uploaded template {name}",
        )
        return template

    def list(self, household_id: str) -> list[PdfTemplate]:
        stmt = select(PdfTemplate).where(PdfTemplate.household_id == household_id)
        return list(self.db.scalars(stmt))

    def get(self, household_id: str, template_id: str) -> PdfTemplate:
        template = self.db.get(PdfTemplate, template_id)
        if template is None or template.household_id != household_id:
            raise DomainError("Template not found", 404)
        return template

    def replace_placeholders(
        self, household_id: str, template_id: str, placeholders, actor
    ) -> PdfTemplate:
        template = self.get(household_id, template_id)
        template.placeholders.clear()
        self.db.flush()
        for item in placeholders:
            template.placeholders.append(
                PdfPlaceholder(
                    binding=item.binding,
                    page=item.page,
                    x=item.x,
                    y=item.y,
                    width=item.width,
                    height=item.height,
                    font_size=item.font_size,
                    align=item.align,
                )
            )
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="pdf_template",
            entity_id=template.id,
            summary="Updated PDF placeholders",
        )
        return template

    def delete(self, household_id: str, template_id: str, actor) -> None:
        template = self.get(household_id, template_id)
        path = template.storage_path
        name = template.name
        self.db.delete(template)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="delete",
            entity_type="pdf_template",
            entity_id=template_id,
            summary=f"Deleted template {name}",
        )
        with suppress(OSError):
            Path(path).unlink(missing_ok=True)

    def resolve_value(self, binding: str, entry: LogEntry) -> str:
        member = (
            self.db.get(HouseholdMember, entry.subject_member_id)
            if entry.subject_member_id
            else None
        )
        profile = member.profile if member else None
        if binding.startswith("payload."):
            key = binding.split(".", 1)[1]
            value = entry.payload.get(key, "")
        elif binding == "member.legal_name":
            value = legal_name(profile)
        elif binding == "member.first_name":
            value = profile.first_name if profile else ""
        elif binding == "member.last_name":
            value = profile.last_name if profile else ""
        elif binding == "member.dob":
            value = (
                profile.date_of_birth.isoformat()
                if profile and profile.date_of_birth
                else ""
            )
        elif binding == "log.occurred_at":
            value = entry.occurred_at.isoformat(sep=" ", timespec="minutes")
        elif binding == "log.form_name":
            value = get_form_type(entry.form_type_code).name
        elif binding == "log.status":
            value = entry.status
        elif binding == "medication.name":
            value = entry.payload.get("medication_name", "")
        else:
            value = ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)

    def export_log(self, household_id: str, template_id: str, log_id: str) -> bytes:
        from app.services.pdf_overlay import overlay_pdf

        template = self.get(household_id, template_id)
        entry = self.db.get(LogEntry, log_id)
        if entry is None or entry.household_id != household_id:
            raise DomainError("Log not found", 404)
        values = {
            ph.binding: self.resolve_value(ph.binding, entry)
            for ph in template.placeholders
        }
        source = self.files.read(template.storage_path)
        return overlay_pdf(source, template.placeholders, values)


class DisciplineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.households = HouseholdService(db)
        self.logs = LogService(db)

    def create(
        self, household_id: str, data: DisciplineIn, actor, recorder
    ) -> DisciplineRecord:
        self.households.get_member(household_id, data.member_id)
        log = self.logs.create(
            household_id,
            LogCreate(
                form_type_code="incident",
                subject_member_id=data.member_id,
                occurred_at=data.occurred_at,
                payload={
                    "severity": "moderate",
                    "location": data.location or "Home",
                    "what_happened": data.behavior,
                    "people_involved": [],
                    "injury": False,
                    "notified": data.notified,
                    "follow_up": data.follow_up or "",
                },
                submit=True,
            ),
            actor,
            recorder,
        )
        record = DisciplineRecord(
            household_id=household_id,
            member_id=data.member_id,
            occurred_at=to_utc_naive(data.occurred_at),
            location=data.location,
            antecedent=data.antecedent,
            behavior=data.behavior,
            intervention=data.intervention,
            consequence=data.consequence,
            duration_minutes=data.duration_minutes,
            follow_up=data.follow_up,
            notified=data.notified,
            log_entry_id=log.id,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list(
        self, household_id: str, member_id: str | None = None
    ) -> list[DisciplineRecord]:
        stmt = select(DisciplineRecord).where(
            DisciplineRecord.household_id == household_id
        )
        if member_id:
            stmt = stmt.where(DisciplineRecord.member_id == member_id)
        stmt = stmt.order_by(DisciplineRecord.occurred_at.desc())
        return list(self.db.scalars(stmt))


class EducationService:
    def __init__(self, db: Session, files: LocalFileStore | None = None) -> None:
        self.db = db
        self.households = HouseholdService(db)
        self.files = files or LocalFileStore()

    def add_enrollment(
        self, household_id: str, data: EnrollmentIn, actor
    ) -> SchoolEnrollment:
        self.households.get_member(household_id, data.member_id)
        enrollment = SchoolEnrollment(household_id=household_id, **data.model_dump())
        self.db.add(enrollment)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="enrollment",
            entity_id=enrollment.id,
            summary=f"Enrolled at {data.school_name}",
        )
        return enrollment

    def list_enrollments(self, household_id: str, member_id: str | None = None):
        stmt = select(SchoolEnrollment).where(
            SchoolEnrollment.household_id == household_id
        )
        if member_id:
            stmt = stmt.where(SchoolEnrollment.member_id == member_id)
        return list(self.db.scalars(stmt))

    def add_grade(
        self, household_id: str, enrollment_id: str, data: GradeIn, actor
    ) -> CourseGrade:
        enrollment = self.db.get(SchoolEnrollment, enrollment_id)
        if enrollment is None or enrollment.household_id != household_id:
            raise DomainError("Enrollment not found", 404)
        grade = CourseGrade(enrollment_id=enrollment.id, **data.model_dump())
        self.db.add(grade)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="grade",
            entity_id=grade.id,
            summary=f"{data.course} {data.term}",
        )
        return grade

    def add_report_card(
        self,
        household_id: str,
        enrollment_id: str,
        term: str,
        filename: str,
        data: bytes,
        actor,
        issued_on=None,
        notes=None,
    ) -> ReportCard:
        enrollment = self.db.get(SchoolEnrollment, enrollment_id)
        if enrollment is None or enrollment.household_id != household_id:
            raise DomainError("Enrollment not found", 404)
        path = self.files.save(
            household_id, f"report-cards/{enrollment_id}", filename, data
        )
        card = ReportCard(
            enrollment_id=enrollment.id,
            term=term,
            issued_on=issued_on,
            storage_path=path,
            filename=filename,
            notes=notes,
        )
        self.db.add(card)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="report_card",
            entity_id=card.id,
            summary=f"Report card {term}",
        )
        return card


class DocumentService:
    def __init__(self, db: Session, files: LocalFileStore | None = None) -> None:
        self.db = db
        self.files = files or LocalFileStore()

    def create(
        self,
        household_id: str,
        *,
        member_id: str | None,
        category: str,
        title: str,
        filename: str,
        content_type: str,
        data: bytes,
        notes: str | None,
        actor,
    ) -> Document:
        path = self.files.save(household_id, f"documents/{category}", filename, data)
        doc = Document(
            household_id=household_id,
            member_id=member_id,
            category=category,
            title=title,
            filename=filename,
            content_type=content_type,
            storage_path=path,
            notes=notes,
        )
        self.db.add(doc)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="document",
            entity_id=doc.id,
            summary=title,
        )
        return doc

    def list(self, household_id: str, member_id: str | None = None) -> list[Document]:
        stmt = select(Document).where(Document.household_id == household_id)
        if member_id:
            stmt = stmt.where(Document.member_id == member_id)
        stmt = stmt.order_by(Document.created_at.desc())
        return list(self.db.scalars(stmt))


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.households = HouseholdService(db)
        self.logs = LogService(db)

    def snapshot(self, household_id: str) -> dict:
        members = self.households.list_members(household_id, include_inactive=True)
        active = [m for m in members if m.status == "active"]
        inactive = [m for m in members if m.status != "active"]
        drafts = self.logs.list_logs(household_id, status="draft")
        recent = self.logs.list_logs(household_id)[:10]
        meds_due = []
        now = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        for member in active:
            profile = member.profile
            if not profile:
                continue
            for med in profile.medications:
                if med.is_prn or not is_administerable(
                    active=med.active,
                    start_date=med.start_date,
                    end_date=med.end_date,
                    on=date.today(),
                ):
                    continue
                times = med.schedule_times or []
                for when in times:
                    given_today = any(
                        entry.form_type_code == "medication_administration"
                        and entry.subject_member_id == member.id
                        and entry.occurred_at.strftime("%Y-%m-%d") == today
                        and entry.payload.get("medication_id") == med.id
                        and entry.status != "draft"
                        for entry in recent
                    )
                    if not given_today:
                        meds_due.append(
                            {
                                "member_id": member.id,
                                "member_name": legal_name(profile),
                                "medication_id": med.id,
                                "medication_name": med.name,
                                "dose": med.dose,
                                "scheduled_time": when,
                                "is_overdue": when <= now,
                            }
                        )
        visits = [
            serialize_log(entry, self.db)
            for entry in self.logs.list_logs(household_id)
            if entry.form_type_code
            in {"case_worker_visit", "court_hearing", "family_visit"}
        ][:8]
        return {
            "active_members": len(active),
            "inactive_members": len(inactive),
            "drafts": len(drafts),
            "meds_due": meds_due,
            "recent_logs": [serialize_log(entry, self.db) for entry in recent],
            "upcoming": visits,
            "members": [serialize_member(m) for m in active],
        }


def serialize_medication(item: Medication) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "dose": item.dose,
        "route": item.route,
        "frequency": item.frequency,
        "schedule_times": item.schedule_times or [],
        "instructions": item.instructions,
        "is_prn": item.is_prn,
        "is_psychotropic": item.is_psychotropic,
        "prescriber": item.prescriber,
        "diagnosis": item.diagnosis,
        "start_date": item.start_date.isoformat() if item.start_date else None,
        "end_date": item.end_date.isoformat() if item.end_date else None,
        "hold_reason": item.hold_reason,
        "active": item.active,
        "flags": list(item.flags or []),
    }


def serialize_member(member: HouseholdMember) -> dict:
    profile = member.profile
    return {
        "id": member.id,
        "household_id": member.household_id,
        "household_role": member.household_role,
        "status": member.status,
        "activated_on": (
            member.activated_on.isoformat() if member.activated_on else None
        ),
        "deactivated_on": (
            member.deactivated_on.isoformat() if member.deactivated_on else None
        ),
        "inactive_reason": member.inactive_reason,
        "login_status": member.login_status,
        "email": member.email,
        "auth_subject": member.auth_subject,
        "idp_role": member.idp_role,
        "invited_at": member.invited_at.isoformat() if member.invited_at else None,
        "first_login_at": (
            member.first_login_at.isoformat() if member.first_login_at else None
        ),
        "legal_name": legal_name(profile),
        "first_name": profile.first_name if profile else None,
        "last_name": profile.last_name if profile else None,
        "preferred_name": profile.preferred_name if profile else None,
        "has_photo": bool(profile and profile.photo_path),
        "date_of_birth": (
            profile.date_of_birth.isoformat()
            if profile and profile.date_of_birth
            else None
        ),
    }


def serialize_profile(profile: PersonProfile) -> dict:
    def dump(items, fields):
        rows = []
        for item in items:
            rows.append({"id": item.id, **{f: getattr(item, f) for f in fields}})
        return rows

    return {
        "id": profile.id,
        "member_id": profile.member_id,
        "first_name": profile.first_name,
        "middle_name": profile.middle_name,
        "last_name": profile.last_name,
        "preferred_name": profile.preferred_name,
        "date_of_birth": (
            profile.date_of_birth.isoformat() if profile.date_of_birth else None
        ),
        "sex": profile.sex,
        "gender": profile.gender,
        "pronouns": profile.pronouns,
        "has_photo": bool(profile.photo_path),
        "medicaid_id": profile.medicaid_id,
        "insurance_provider": profile.insurance_provider,
        "insurance_policy": profile.insurance_policy,
        "insurance_group": profile.insurance_group,
        "placement_start": (
            profile.placement_start.isoformat() if profile.placement_start else None
        ),
        "placement_end": (
            profile.placement_end.isoformat() if profile.placement_end else None
        ),
        "school_name": profile.school_name,
        "school_grade": profile.school_grade,
        "teacher": profile.teacher,
        "counselor": profile.counselor,
        "clothing_shirt": profile.clothing_shirt,
        "clothing_pants": profile.clothing_pants,
        "clothing_shoes": profile.clothing_shoes,
        "notes": profile.notes,
        "allergies": dump(
            profile.allergies, ["allergen", "severity", "reaction", "verified_on"]
        ),
        "medications": [serialize_medication(item) for item in profile.medications],
        "diagnoses": dump(
            profile.diagnoses, ["name", "code", "onset", "status", "notes"]
        ),
        "disabilities": dump(profile.disabilities, ["name", "accommodations", "notes"]),
        "clinicians": dump(
            profile.clinicians, ["role", "name", "clinic", "phone", "fax", "address"]
        ),
        "professional_contacts": dump(
            profile.professional_contacts,
            ["role", "name", "agency", "phone", "email", "visit_cadence"],
        ),
        "emergency_contacts": dump(
            profile.emergency_contacts,
            ["name", "relationship", "phone", "email", "address", "is_primary"],
        ),
        "otc_medications": [
            serialize_assignment(item) for item in profile.otc_assignments
        ],
    }


def serialize_log(entry: LogEntry, db: Session) -> dict:
    member_name = None
    if entry.subject_member_id:
        member = db.get(HouseholdMember, entry.subject_member_id)
        member_name = legal_name(member.profile) if member else None
    return {
        "id": entry.id,
        "household_id": entry.household_id,
        "form_type_code": entry.form_type_code,
        "form_name": get_form_type(entry.form_type_code).name,
        "subject_member_id": entry.subject_member_id,
        "subject_name": member_name,
        "recorded_by_id": entry.recorded_by_id,
        "occurred_at": iso_utc(entry.occurred_at),
        "status": entry.status,
        "payload": entry.payload,
        "amended_from_id": entry.amended_from_id,
        "attachments": [
            {"id": a.id, "filename": a.filename, "content_type": a.content_type}
            for a in entry.attachments
        ],
    }
