from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.auth.management import IdentityDirectory, NoOpDirectory
from app.core.errors import DomainError
from app.models import (
    Allergy,
    AuditEvent,
    Clinician,
    Diagnosis,
    Disability,
    EmergencyContact,
    Household,
    HouseholdMember,
    Medication,
    PersonProfile,
    ProfessionalContact,
)
from app.schemas import HouseholdCreate, MemberCreate, ProfileUpdate
from app.services.identity import link_first_login, normalize_email


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def audit(
    db: Session,
    *,
    household_id: str | None,
    actor_subject: str,
    actor_email: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    summary: str,
) -> None:
    db.add(
        AuditEvent(
            household_id=household_id,
            actor_subject=actor_subject,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
        )
    )


def legal_name(profile: PersonProfile | None) -> str:
    if profile is None:
        return "Unknown"
    preferred = profile.preferred_name or profile.first_name
    return f"{preferred} {profile.last_name}".strip()


class HouseholdService:
    def __init__(
        self,
        db: Session,
        directory: IdentityDirectory | None = None,
    ) -> None:
        self.db = db
        self.directory = directory or NoOpDirectory()

    def create_household(self, data: HouseholdCreate, actor) -> Household:
        household = Household(**data.model_dump())
        self.db.add(household)
        self.db.flush()
        member = HouseholdMember(
            household_id=household.id,
            household_role="admin",
            status="active",
            activated_on=date.today(),
            login_status="linked",
            email=normalize_email(actor.email),
            auth_subject=actor.subject,
            first_login_at=_now(),
            idp_role="Household Admin",
        )
        self.db.add(member)
        self.db.flush()
        email_local = (actor.email or "admin").split("@")[0]
        profile = PersonProfile(
            member_id=member.id,
            first_name=email_local[:1].upper() + email_local[1:32],
            last_name="Admin",
        )
        self.db.add(profile)
        member.profile = profile
        audit(
            self.db,
            household_id=household.id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="household",
            entity_id=household.id,
            summary=f"Created household {household.name}",
        )
        self.db.flush()
        return household

    def list_for_actor(self, actor) -> list[Household]:
        stmt = (
            select(Household)
            .join(HouseholdMember)
            .where(
                or_(
                    HouseholdMember.auth_subject == actor.subject,
                    HouseholdMember.email == normalize_email(actor.email),
                )
            )
            .distinct()
        )
        return list(self.db.scalars(stmt))

    def get(self, household_id: str) -> Household:
        household = self.db.get(Household, household_id)
        if household is None:
            raise DomainError("Household not found", 404)
        return household

    def update(self, household_id: str, data, actor) -> Household:
        household = self.get(household_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(household, key, value)
        audit(
            self.db,
            household_id=household.id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="household",
            entity_id=household.id,
            summary="Updated household settings",
        )
        return household

    def require_membership(self, household_id: str, actor) -> HouseholdMember:
        self.link_pending(actor)
        stmt = select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            or_(
                HouseholdMember.auth_subject == actor.subject,
                HouseholdMember.email == normalize_email(actor.email),
            ),
        )
        member = self.db.scalars(stmt).first()
        if member is None:
            raise DomainError("Not a member of this household", 403)
        if member.login_status == "pending":
            raise DomainError("Account is pending first login", 403)
        if member.status != "active":
            raise DomainError("Membership is inactive", 403)
        return member

    def link_pending(self, actor) -> list[HouseholdMember]:
        if not actor.email:
            stmt = select(HouseholdMember).where(
                HouseholdMember.auth_subject == actor.subject
            )
            return list(self.db.scalars(stmt))
        stmt = select(HouseholdMember).where(
            or_(
                HouseholdMember.auth_subject == actor.subject,
                HouseholdMember.email == normalize_email(actor.email),
            )
        )
        linked = []
        for member in self.db.scalars(stmt):
            link_first_login(
                member, subject=actor.subject, email=actor.email, now=_now()
            )
            linked.append(member)
        return linked

    def list_members(
        self, household_id: str, *, include_inactive: bool = False
    ) -> list[HouseholdMember]:
        stmt: Select = (
            select(HouseholdMember)
            .options(joinedload(HouseholdMember.profile))
            .where(HouseholdMember.household_id == household_id)
        )
        if not include_inactive:
            stmt = stmt.where(HouseholdMember.status == "active")
        return list(self.db.scalars(stmt).unique())

    def add_member(
        self, household_id: str, data: MemberCreate, actor
    ) -> HouseholdMember:
        login_status = "none"
        invited_at = None
        should_invite = bool(data.email) and (
            data.invite or data.household_role in {"admin", "adult"}
        )
        if should_invite:
            login_status = "pending"
            invited_at = _now()
            if data.invite:
                self.directory.invite(str(data.email), data.idp_role)
        member = HouseholdMember(
            household_id=household_id,
            household_role=data.household_role,
            status="active",
            activated_on=data.activated_on or date.today(),
            login_status=login_status,
            email=normalize_email(str(data.email) if data.email else None),
            idp_role=data.idp_role,
            invited_at=invited_at,
        )
        self.db.add(member)
        self.db.flush()
        profile = PersonProfile(
            member_id=member.id,
            first_name=data.first_name,
            middle_name=data.middle_name,
            last_name=data.last_name,
            preferred_name=data.preferred_name,
            date_of_birth=data.date_of_birth,
        )
        self.db.add(profile)
        member.profile = profile
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type="member",
            entity_id=member.id,
            summary=f"Added member {data.first_name} {data.last_name}",
        )
        self.db.flush()
        return member

    def get_member(self, household_id: str, member_id: str) -> HouseholdMember:
        member = self.db.get(HouseholdMember, member_id)
        if member is None or member.household_id != household_id:
            raise DomainError("Member not found", 404)
        return member

    def update_member(
        self, household_id: str, member_id: str, data, actor
    ) -> HouseholdMember:
        member = self.get_member(household_id, member_id)
        payload = data.model_dump(exclude_unset=True)
        if "email" in payload and payload["email"]:
            payload["email"] = normalize_email(str(payload["email"]))
        for key, value in payload.items():
            setattr(member, key, value)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="member",
            entity_id=member.id,
            summary="Updated member",
        )
        return member

    def invite(self, household_id: str, member_id: str, actor) -> HouseholdMember:
        member = self.get_member(household_id, member_id)
        if not member.email:
            raise DomainError("Member has no email to invite")
        self.directory.invite(member.email, member.idp_role)
        member.login_status = "pending"
        member.invited_at = _now()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="invite",
            entity_type="member",
            entity_id=member.id,
            summary=f"Invited {member.email}",
        )
        return member

    def deactivate(
        self, household_id: str, member_id: str, data, actor
    ) -> HouseholdMember:
        member = self.get_member(household_id, member_id)
        member.status = "inactive"
        member.deactivated_on = data.effective_on or date.today()
        member.inactive_reason = data.reason
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="deactivate",
            entity_type="member",
            entity_id=member.id,
            summary=data.reason or "Deactivated member",
        )
        return member

    def activate(
        self, household_id: str, member_id: str, data, actor
    ) -> HouseholdMember:
        member = self.get_member(household_id, member_id)
        member.status = "active"
        member.activated_on = data.effective_on or date.today()
        member.deactivated_on = None
        member.inactive_reason = None
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="activate",
            entity_type="member",
            entity_id=member.id,
            summary="Reactivated member",
        )
        return member


NESTED = {
    "allergies": (Allergy, "allergen"),
    "medications": (Medication, "name"),
    "diagnoses": (Diagnosis, "name"),
    "disabilities": (Disability, "name"),
    "clinicians": (Clinician, "name"),
    "professional_contacts": (ProfessionalContact, "name"),
    "emergency_contacts": (EmergencyContact, "name"),
}


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.households = HouseholdService(db)

    def get_profile(self, household_id: str, member_id: str) -> PersonProfile:
        member = self.households.get_member(household_id, member_id)
        if member.profile is None:
            raise DomainError("Profile not found", 404)
        return member.profile

    def update_profile(
        self, household_id: str, member_id: str, data: ProfileUpdate, actor
    ) -> PersonProfile:
        profile = self.get_profile(household_id, member_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="profile",
            entity_id=profile.id,
            summary="Updated profile",
        )
        return profile

    def add_nested(
        self, household_id: str, member_id: str, collection: str, data, actor
    ):
        if collection not in NESTED:
            raise DomainError("Unknown collection", 404)
        model, _ = NESTED[collection]
        profile = self.get_profile(household_id, member_id)
        item = model(profile_id=profile.id, **data.model_dump())
        self.db.add(item)
        self.db.flush()
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="create",
            entity_type=collection,
            entity_id=item.id,
            summary=f"Added {collection} item",
        )
        return item

    def update_nested(
        self,
        household_id: str,
        member_id: str,
        collection: str,
        item_id: str,
        data,
        actor,
    ):
        if collection not in NESTED:
            raise DomainError("Unknown collection", 404)
        model, _ = NESTED[collection]
        profile = self.get_profile(household_id, member_id)
        item = self.db.get(model, item_id)
        if item is None or item.profile_id != profile.id:
            raise DomainError("Item not found", 404)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type=collection,
            entity_id=item.id,
            summary=f"Updated {collection} item",
        )
        return item

    def delete_nested(
        self, household_id: str, member_id: str, collection: str, item_id: str, actor
    ) -> None:
        if collection not in NESTED:
            raise DomainError("Unknown collection", 404)
        model, _ = NESTED[collection]
        profile = self.get_profile(household_id, member_id)
        item = self.db.get(model, item_id)
        if item is None or item.profile_id != profile.id:
            raise DomainError("Item not found", 404)
        self.db.delete(item)
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="delete",
            entity_type=collection,
            entity_id=item_id,
            summary=f"Removed {collection} item",
        )

    def set_photo(
        self, household_id: str, member_id: str, path: str, actor
    ) -> PersonProfile:
        profile = self.get_profile(household_id, member_id)
        profile.photo_path = path
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="profile",
            entity_id=profile.id,
            summary="Updated photo",
        )
        return profile
