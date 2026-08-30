from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.med_rules import normalize_med_flags

HouseholdType = Literal["family", "foster", "mixed"]
MemberRole = Literal["admin", "adult", "child", "other"]
MemberStatus = Literal["active", "inactive"]
LoginStatus = Literal["none", "pending", "linked"]
LogStatus = Literal["draft", "submitted", "amended"]


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    household_type: HouseholdType = "family"
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str = "America/Chicago"
    phone: str | None = None
    agency_name: str | None = None
    licensing_worker: str | None = None
    license_number: str | None = None
    capacity: int | None = None


class HouseholdUpdate(BaseModel):
    name: str | None = None
    household_type: HouseholdType | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    phone: str | None = None
    agency_name: str | None = None
    licensing_worker: str | None = None
    license_number: str | None = None
    capacity: int | None = None


class HouseholdOut(HouseholdCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberCreate(BaseModel):
    household_role: MemberRole
    first_name: str
    last_name: str
    middle_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: date | None = None
    email: EmailStr | None = None
    invite: bool = False
    idp_role: str | None = None
    activated_on: date | None = None


class MemberUpdate(BaseModel):
    household_role: MemberRole | None = None
    email: EmailStr | None = None
    idp_role: str | None = None


class MemberStatusUpdate(BaseModel):
    reason: str | None = None
    effective_on: date | None = None


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    preferred_name: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    gender: str | None = None
    pronouns: str | None = None
    medicaid_id: str | None = None
    insurance_provider: str | None = None
    insurance_policy: str | None = None
    insurance_group: str | None = None
    placement_start: date | None = None
    placement_end: date | None = None
    school_name: str | None = None
    school_grade: str | None = None
    teacher: str | None = None
    counselor: str | None = None
    clothing_shirt: str | None = None
    clothing_pants: str | None = None
    clothing_shoes: str | None = None
    notes: str | None = None


class AllergyIn(BaseModel):
    allergen: str
    severity: Literal["mild", "moderate", "severe", "life_threatening"]
    reaction: str | None = None
    verified_on: date | None = None


class MedicationIn(BaseModel):
    name: str
    dose: str
    route: str
    frequency: str
    schedule_times: list[str] = Field(default_factory=list)
    instructions: str | None = None
    is_prn: bool = False
    is_psychotropic: bool = False
    prescriber: str | None = None
    diagnosis: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    hold_reason: str | None = None
    active: bool = True
    flags: list[str] = Field(default_factory=list)

    @field_validator("flags")
    @classmethod
    def known_flags(cls, value: list[str]) -> list[str]:
        return normalize_med_flags(value)


class MedicationUpdate(BaseModel):
    name: str | None = None
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    schedule_times: list[str] | None = None
    instructions: str | None = None
    is_prn: bool | None = None
    is_psychotropic: bool | None = None
    prescriber: str | None = None
    diagnosis: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    hold_reason: str | None = None
    active: bool | None = None
    flags: list[str] | None = None

    @field_validator("flags")
    @classmethod
    def known_flags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return normalize_med_flags(value)


class HouseholdOtcMedicationIn(BaseModel):
    name: str
    dose: str
    route: str = "oral"
    instructions: str | None = None
    active: bool = True


class HouseholdOtcMedicationUpdate(BaseModel):
    name: str | None = None
    dose: str | None = None
    route: str | None = None
    instructions: str | None = None
    active: bool | None = None


class MemberOtcAssignmentIn(BaseModel):
    otc_medication_id: str
    dose: str | None = None
    instructions: str | None = None


class DiagnosisIn(BaseModel):
    name: str
    code: str | None = None
    onset: date | None = None
    status: str = "active"
    notes: str | None = None


class DisabilityIn(BaseModel):
    name: str
    accommodations: str | None = None
    notes: str | None = None


class ClinicianIn(BaseModel):
    role: Literal["pcp", "dentist", "therapist", "psychiatrist", "specialist", "other"]
    name: str
    clinic: str | None = None
    phone: str | None = None
    fax: str | None = None
    address: str | None = None


class ProfessionalContactIn(BaseModel):
    role: Literal[
        "case_worker",
        "adoption_specialist",
        "gal",
        "casa",
        "attorney",
        "licensing_worker",
        "other",
    ]
    name: str
    agency: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    visit_cadence: str | None = None


class EmergencyContactIn(BaseModel):
    name: str
    relationship: str
    phone: str
    email: EmailStr | None = None
    address: str | None = None
    is_primary: bool = False


class LogCreate(BaseModel):
    form_type_code: str
    subject_member_id: str | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    submit: bool = False


class LogAmend(BaseModel):
    payload: dict[str, Any]
    occurred_at: datetime | None = None
    reason: str


class DisciplineIn(BaseModel):
    member_id: str
    occurred_at: datetime
    location: str | None = None
    antecedent: str
    behavior: str
    intervention: str
    consequence: str
    duration_minutes: int | None = None
    follow_up: str | None = None
    notified: list[str] = Field(default_factory=list)


class EnrollmentIn(BaseModel):
    member_id: str
    school_name: str
    campus: str | None = None
    grade_level: str
    school_year: str
    start_date: date | None = None
    end_date: date | None = None
    iep: bool = False
    plan_504: bool = False
    counselor: str | None = None
    teacher: str | None = None


class GradeIn(BaseModel):
    term: str
    course: str
    letter: str | None = None
    percent: str | None = None
    comments: str | None = None


class PlaceholderIn(BaseModel):
    binding: str
    page: int = Field(ge=1)
    x: float
    y: float
    width: float
    height: float
    font_size: int = 10
    align: str = "left"


class PdfTemplateUpdate(BaseModel):
    name: str | None = None
    form_type_code: str | None = None
    placeholders: list[PlaceholderIn] | None = None


class PdfTemplateImport(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    form_type_code: str
    filename: str = "form.pdf"
    content_base64: str


class FormExportRequest(BaseModel):
    form_code: str = Field(min_length=1)
    start_date: date
    end_date: date
    member_ids: list[str] = Field(default_factory=list)


class DocumentIn(BaseModel):
    member_id: str | None = None
    category: str
    title: str
    notes: str | None = None


class PermissionGrant(BaseModel):
    resource: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=32)


class PermissionReplace(BaseModel):
    grants: list[PermissionGrant] = Field(default_factory=list)


class OidcTokenExchange(BaseModel):
    code: str = Field(min_length=1)
    code_verifier: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)
    resource: str | None = None
