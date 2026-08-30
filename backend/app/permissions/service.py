from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.exports.catalog import get_official_export
from app.models import HouseholdMember, MemberPermission
from app.permissions.catalog import (
    all_grants,
    serialize_catalog,
    validate_grant,
)
from app.services.households import HouseholdService, audit
from app.services.identity import normalize_email


def serialize_grant(resource: str, action: str) -> dict:
    return {"resource": resource, "action": action}


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.households = HouseholdService(db)

    def catalog(self) -> list[dict]:
        return serialize_catalog()

    def list_for_member(self, household_id: str, member_id: str) -> list[dict]:
        member = self.households.get_member(household_id, member_id)
        return [
            serialize_grant(resource, action)
            for resource, action in self.stored(member)
        ]

    def effective_for_member(self, member: HouseholdMember) -> list[tuple[str, str]]:
        if member.household_role == "admin":
            return all_grants()
        return self.stored(member)

    def stored(self, member: HouseholdMember) -> list[tuple[str, str]]:
        rows = self.db.scalars(
            select(MemberPermission).where(MemberPermission.member_id == member.id)
        )
        return [(row.resource, row.action) for row in rows]

    def can_member(self, member: HouseholdMember, resource: str, action: str) -> bool:
        if member.household_role == "admin":
            return True
        return (resource, action) in set(self.stored(member))

    def can(self, household_id: str, actor, resource: str, action: str) -> bool:
        member = self.households.require_membership(household_id, actor)
        return self.can_member(member, resource, action)

    def require(self, household_id: str, actor, resource: str, action: str) -> None:
        if not self.can(household_id, actor, resource, action):
            raise DomainError("You do not have permission to do that.", 403)

    def require_form(
        self, household_id: str, actor, form_code: str, action: str
    ) -> None:
        self.require(household_id, actor, f"form.{form_code}", action)

    def require_export(self, household_id: str, actor, form_code: str) -> None:
        self.require(household_id, actor, "tab.export", "view")
        spec = get_official_export(form_code)
        if any(
            self.can(household_id, actor, f"form.{source}", "export")
            for source in spec.source_forms
        ):
            return
        raise DomainError("You do not have permission to export that form.", 403)

    def replace_for_member(
        self, household_id: str, member_id: str, grants: list, actor
    ) -> list[dict]:
        actor_member = self.households.require_membership(household_id, actor)
        if actor_member.household_role != "admin":
            raise DomainError("Only household admins can change permissions.", 403)
        member = self.households.get_member(household_id, member_id)
        pairs: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for grant in grants:
            resource = (
                grant.resource if hasattr(grant, "resource") else grant["resource"]
            )
            action = grant.action if hasattr(grant, "action") else grant["action"]
            validate_grant(resource, action)
            pair = (resource, action)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
        self.db.execute(
            delete(MemberPermission).where(MemberPermission.member_id == member.id)
        )
        for resource, action in pairs:
            self.db.add(
                MemberPermission(member_id=member.id, resource=resource, action=action)
            )
        audit(
            self.db,
            household_id=household_id,
            actor_subject=actor.subject,
            actor_email=actor.email,
            action="update",
            entity_type="member_permissions",
            entity_id=member.id,
            summary=f"Updated permissions for member {member.id}",
        )
        self.db.flush()
        return [serialize_grant(resource, action) for resource, action in pairs]

    def member_for_actor(self, household_id: str, actor) -> HouseholdMember | None:
        email = normalize_email(actor.email) if actor.email else None
        for member in self.households.list_members(household_id, include_inactive=True):
            if member.auth_subject == actor.subject:
                return member
            if email and member.email == email:
                return member
        return None

    def household_payload(self, household, actor) -> dict:
        member = self.member_for_actor(household.id, actor)
        if member is None:
            return {
                "id": household.id,
                "name": household.name,
                "household_type": household.household_type,
                "timezone": household.timezone,
                "member_id": None,
                "household_role": None,
                "permissions": [],
            }
        return {
            "id": household.id,
            "name": household.name,
            "household_type": household.household_type,
            "timezone": household.timezone,
            "member_id": member.id,
            "household_role": member.household_role,
            "permissions": [
                serialize_grant(resource, action)
                for resource, action in self.effective_for_member(member)
            ],
        }
