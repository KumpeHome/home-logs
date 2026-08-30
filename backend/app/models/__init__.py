from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_rel
from sqlalchemy.types import JSON

from app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Household(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    household_type: Mapped[str] = mapped_column(String(32))
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agency_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    licensing_worker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    members: Mapped[list[HouseholdMember]] = orm_rel(back_populates="household")
    otc_medications: Mapped[list[HouseholdOtcMedication]] = orm_rel(
        back_populates="household", cascade="all, delete-orphan"
    )


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    household_role: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="active")
    activated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deactivated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    inactive_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_status: Mapped[str] = mapped_column(String(32), default="none")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    auth_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    idp_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    household: Mapped[Household] = orm_rel(back_populates="members")
    profile: Mapped[PersonProfile | None] = orm_rel(
        back_populates="member", uselist=False
    )
    permissions: Mapped[list[MemberPermission]] = orm_rel(
        back_populates="member", cascade="all, delete-orphan"
    )


class MemberPermission(Base):
    __tablename__ = "member_permissions"
    __table_args__ = (
        UniqueConstraint("member_id", "resource", "action", name="uq_member_perm"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    member_id: Mapped[str] = mapped_column(
        ForeignKey("household_members.id"), index=True
    )
    resource: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(32))

    member: Mapped[HouseholdMember] = orm_rel(back_populates="permissions")


class PersonProfile(Base):
    __tablename__ = "person_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    member_id: Mapped[str] = mapped_column(
        ForeignKey("household_members.id"), unique=True
    )
    first_name: Mapped[str] = mapped_column(String(128))
    middle_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str] = mapped_column(String(128))
    preferred_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    medicaid_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    insurance_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    insurance_policy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    insurance_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    placement_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    placement_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    school_grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    teacher: Mapped[str | None] = mapped_column(String(128), nullable=True)
    counselor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    clothing_shirt: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clothing_pants: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clothing_shoes: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    member: Mapped[HouseholdMember] = orm_rel(back_populates="profile")
    allergies: Mapped[list[Allergy]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    medications: Mapped[list[Medication]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    diagnoses: Mapped[list[Diagnosis]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    disabilities: Mapped[list[Disability]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    clinicians: Mapped[list[Clinician]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    professional_contacts: Mapped[list[ProfessionalContact]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    emergency_contacts: Mapped[list[EmergencyContact]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )
    otc_assignments: Mapped[list[MemberOtcAssignment]] = orm_rel(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    allergen: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    reaction: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verified_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="allergies")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(128))
    route: Mapped[str] = mapped_column(String(64))
    frequency: Mapped[str] = mapped_column(String(128))
    schedule_times: Mapped[list] = mapped_column(JSON, default=list)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_prn: Mapped[bool] = mapped_column(Boolean, default=False)
    is_psychotropic: Mapped[bool] = mapped_column(Boolean, default=False)
    prescriber: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hold_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    flags: Mapped[list] = mapped_column(JSON, default=list)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="medications")


class HouseholdOtcMedication(Base):
    __tablename__ = "household_otc_medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(128))
    route: Mapped[str] = mapped_column(String(64), default="oral")
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    household: Mapped[Household] = orm_rel(back_populates="otc_medications")
    assignments: Mapped[list[MemberOtcAssignment]] = orm_rel(
        back_populates="otc", cascade="all, delete-orphan"
    )


class MemberOtcAssignment(Base):
    __tablename__ = "member_otc_assignments"
    __table_args__ = (
        UniqueConstraint("profile_id", "otc_medication_id", name="uq_member_otc"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    otc_medication_id: Mapped[str] = mapped_column(
        ForeignKey("household_otc_medications.id", ondelete="CASCADE"), index=True
    )
    dose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="otc_assignments")
    otc: Mapped[HouseholdOtcMedication] = orm_rel(back_populates="assignments")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    onset: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="diagnoses")


class Disability(Base):
    __tablename__ = "disabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    accommodations: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="disabilities")


class Clinician(Base):
    __tablename__ = "clinicians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    clinic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="clinicians")


class ProfessionalContact(Base):
    __tablename__ = "professional_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    agency: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visit_cadence: Mapped[str | None] = mapped_column(String(128), nullable=True)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="professional_contacts")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("person_profiles.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    relationship: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped[PersonProfile] = orm_rel(back_populates="emergency_contacts")


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    form_type_code: Mapped[str] = mapped_column(String(64), index=True)
    subject_member_id: Mapped[str | None] = mapped_column(
        ForeignKey("household_members.id"), nullable=True
    )
    recorded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("household_members.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    amended_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("log_entries.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    attachments: Mapped[list[LogAttachment]] = orm_rel(
        back_populates="log_entry", cascade="all, delete-orphan"
    )


class LogAttachment(Base):
    __tablename__ = "log_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    log_entry_id: Mapped[str] = mapped_column(ForeignKey("log_entries.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    storage_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    log_entry: Mapped[LogEntry] = orm_rel(back_populates="attachments")


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    form_type_code: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    placeholders: Mapped[list[PdfPlaceholder]] = orm_rel(
        back_populates="template", cascade="all, delete-orphan"
    )


class PdfPlaceholder(Base):
    __tablename__ = "pdf_placeholders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("pdf_templates.id"), index=True)
    binding: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer)
    x: Mapped[float] = mapped_column()
    y: Mapped[float] = mapped_column()
    width: Mapped[float] = mapped_column()
    height: Mapped[float] = mapped_column()
    font_size: Mapped[int] = mapped_column(Integer, default=10)
    align: Mapped[str] = mapped_column(String(16), default="left")

    template: Mapped[PdfTemplate] = orm_rel(back_populates="placeholders")


class DisciplineRecord(Base):
    __tablename__ = "discipline_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    member_id: Mapped[str] = mapped_column(
        ForeignKey("household_members.id"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    antecedent: Mapped[str] = mapped_column(Text)
    behavior: Mapped[str] = mapped_column(Text)
    intervention: Mapped[str] = mapped_column(Text)
    consequence: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    notified: Mapped[list] = mapped_column(JSON, default=list)
    log_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("log_entries.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SchoolEnrollment(Base):
    __tablename__ = "school_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    member_id: Mapped[str] = mapped_column(
        ForeignKey("household_members.id"), index=True
    )
    school_name: Mapped[str] = mapped_column(String(255))
    campus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade_level: Mapped[str] = mapped_column(String(32))
    school_year: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    iep: Mapped[bool] = mapped_column(Boolean, default=False)
    plan_504: Mapped[bool] = mapped_column(Boolean, default=False)
    counselor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    teacher: Mapped[str | None] = mapped_column(String(128), nullable=True)

    grades: Mapped[list[CourseGrade]] = orm_rel(
        back_populates="enrollment", cascade="all, delete-orphan"
    )
    report_cards: Mapped[list[ReportCard]] = orm_rel(
        back_populates="enrollment", cascade="all, delete-orphan"
    )


class CourseGrade(Base):
    __tablename__ = "course_grades"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "term", "course", name="uq_grade_enrollment_term_course"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("school_enrollments.id"), index=True
    )
    term: Mapped[str] = mapped_column(String(64))
    course: Mapped[str] = mapped_column(String(128))
    letter: Mapped[str | None] = mapped_column(String(8), nullable=True)
    percent: Mapped[str | None] = mapped_column(String(16), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    enrollment: Mapped[SchoolEnrollment] = orm_rel(back_populates="grades")


class ReportCard(Base):
    __tablename__ = "report_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("school_enrollments.id"), index=True
    )
    term: Mapped[str] = mapped_column(String(64))
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    enrollment: Mapped[SchoolEnrollment] = orm_rel(back_populates="report_cards")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    member_id: Mapped[str | None] = mapped_column(
        ForeignKey("household_members.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    storage_path: Mapped[str] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    household_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    actor_subject: Mapped[str] = mapped_column(String(255))
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
