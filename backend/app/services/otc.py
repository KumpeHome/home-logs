from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models import (
    HouseholdOtcMedication,
    Medication,
    MemberOtcAssignment,
    PersonProfile,
)
from app.schemas import (
    HouseholdOtcMedicationIn,
    HouseholdOtcMedicationUpdate,
    MemberOtcAssignmentIn,
)
from app.services.households import HouseholdService, audit
from app.services.med_rules import is_administerable


def serialize_otc(item: HouseholdOtcMedication) -> dict:
    return {
        "id": item.id,
        "household_id": item.household_id,
        "name": item.name,
        "dose": item.dose,
        "route": item.route,
        "instructions": item.instructions,
        "active": item.active,
    }


def serialize_assignment(item: MemberOtcAssignment) -> dict:
    otc = item.otc
    return {
        "id": item.id,
        "otc_medication_id": item.otc_medication_id,
        "name": otc.name,
        "dose": item.dose or otc.dose,
        "route": otc.route,
        "instructions": item.instructions or otc.instructions,
        "active": item.active and otc.active,
        "is_otc": True,
    }


class OtcService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.households = HouseholdService(db)

    def list_catalog(self, household_id: str) -> list[HouseholdOtcMedication]:
        stmt = (
            select(HouseholdOtcMedication)
            .where(HouseholdOtcMedication.household_id == household_id)
            .order_by(HouseholdOtcMedication.name)
        )
        return list(self.db.scalars(stmt))

    def add_catalog(
        self, household_id: str, data: HouseholdOtcMedicationIn, actor
    ) -> HouseholdOtcMedication:
        self.households.get(household_id)
        item = HouseholdOtcMedication(household_id=household_id, **data.model_dump())
        self.db.add(item)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="otc_medication",
            entity_id=item.id,
            summary=f"Added household OTC {item.name}",
        )
        return item

    def get_catalog_item(
        self, household_id: str, otc_id: str
    ) -> HouseholdOtcMedication:
        item = self.db.get(HouseholdOtcMedication, otc_id)
        if item is None or item.household_id != household_id:
            raise DomainError("OTC medication not found", 404)
        return item

    def update_catalog(
        self,
        household_id: str,
        otc_id: str,
        data: HouseholdOtcMedicationUpdate,
        actor,
    ) -> HouseholdOtcMedication:
        item = self.get_catalog_item(household_id, otc_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="otc_medication",
            entity_id=item.id,
            summary=f"Updated household OTC {item.name}",
        )
        return item

    def delete_catalog(self, household_id: str, otc_id: str, actor) -> None:
        item = self.get_catalog_item(household_id, otc_id)
        self.db.delete(item)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="delete",
            entity_type="otc_medication",
            entity_id=otc_id,
            summary=f"Removed household OTC {item.name}",
        )

    def assign(
        self, household_id: str, member_id: str, data: MemberOtcAssignmentIn, actor
    ) -> MemberOtcAssignment:
        member = self.households.get_member(household_id, member_id)
        profile = member.profile
        if profile is None:
            raise DomainError("Profile not found", 404)
        otc = self.get_catalog_item(household_id, data.otc_medication_id)
        if not otc.active:
            raise DomainError("OTC medication is not active")
        existing = self.db.scalar(
            select(MemberOtcAssignment).where(
                MemberOtcAssignment.profile_id == profile.id,
                MemberOtcAssignment.otc_medication_id == otc.id,
            )
        )
        if existing is not None:
            raise DomainError("OTC medication is already assigned to this member")
        assignment = MemberOtcAssignment(
            profile_id=profile.id,
            otc_medication_id=otc.id,
            dose=data.dose,
            instructions=data.instructions,
        )
        self.db.add(assignment)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="member_otc",
            entity_id=assignment.id,
            summary=f"Assigned OTC {otc.name}",
        )
        return assignment

    def unassign(
        self, household_id: str, member_id: str, assignment_id: str, actor
    ) -> None:
        member = self.households.get_member(household_id, member_id)
        profile = member.profile
        if profile is None:
            raise DomainError("Profile not found", 404)
        assignment = self.db.get(MemberOtcAssignment, assignment_id)
        if assignment is None or assignment.profile_id != profile.id:
            raise DomainError("OTC assignment not found", 404)
        self.db.delete(assignment)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="delete",
            entity_type="member_otc",
            entity_id=assignment_id,
            summary="Removed OTC assignment",
        )


def _profile_medication(
    db: Session, profile: PersonProfile, medication_id: str, on: date
) -> tuple[str, str, str, bool] | None:
    med = db.get(Medication, medication_id)
    if med is None or med.profile_id != profile.id:
        return None
    if not med.active:
        raise DomainError("Medication is not active")
    if not is_administerable(
        active=True, start_date=med.start_date, end_date=med.end_date, on=on
    ):
        raise DomainError("Medication is outside its start/end date window")
    return med.name, med.dose, med.route, med.is_psychotropic


def _assigned_otc(
    db: Session,
    household_id: str,
    profile: PersonProfile,
    medication_id: str,
    _on: date,
) -> tuple[str, str, str, bool] | None:
    assignment = db.get(MemberOtcAssignment, medication_id)
    if assignment is None or assignment.profile_id != profile.id:
        return None
    if assignment.otc.household_id != household_id:
        return None
    if not assignment.active or not assignment.otc.active:
        raise DomainError("Medication is not active")
    return (
        assignment.otc.name,
        assignment.dose or assignment.otc.dose,
        assignment.otc.route,
        False,
    )


def resolve_administered_medication(
    db: Session,
    household_id: str,
    profile: PersonProfile | None,
    medication_id: str | None,
    on: date | None = None,
) -> tuple[str, str, str, bool]:
    """Return name, dose, route, is_psychotropic for a profile med or OTC assignment."""
    if not medication_id or profile is None:
        raise DomainError("Select a medication from this member's profile")
    when = on or date.today()
    resolved = _profile_medication(db, profile, medication_id, when) or _assigned_otc(
        db, household_id, profile, medication_id, when
    )
    if resolved is None:
        raise DomainError("Select a medication from this member's profile")
    return resolved
