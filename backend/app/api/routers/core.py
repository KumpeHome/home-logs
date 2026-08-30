from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, household_service, require_scopes
from app.core.auth.scopes import ADMIN_AUDIT, HOUSEHOLD_MANAGE, HOUSEHOLD_READ
from app.core.auth.token import exchange_authorization_code
from app.core.auth.user import AuthUser
from app.core.config import get_settings
from app.db.session import get_db
from app.models import AuditEvent, Household
from app.permissions.service import PermissionService
from app.schemas import HouseholdCreate, HouseholdUpdate, OidcTokenExchange
from app.services.households import HouseholdService

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "name": "Home Logs",
        "auth_bypass": settings.auth_disabled,
    }


@router.post("/auth/token")
def exchange_oidc_token(data: OidcTokenExchange) -> dict:
    return exchange_authorization_code(
        get_settings(),
        code=data.code,
        code_verifier=data.code_verifier,
        redirect_uri=data.redirect_uri,
        resource=data.resource,
    )


@router.get("/me")
def me(
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    members = service.link_pending(user)
    households = service.list_for_actor(user)
    linked = [m for m in members if m.login_status == "linked"]
    pending = [m for m in members if m.login_status == "pending"]
    return {
        "subject": user.subject,
        "email": user.email,
        "name": user.name,
        "scopes": sorted(user.scopes),
        "linked": bool(linked) or bool(households),
        "pending_memberships": [
            {"household_id": m.household_id, "member_id": m.id} for m in pending
        ],
        "households": [
            PermissionService(service.db).household_payload(h, user) for h in households
        ],
    }


@router.get("/permission-catalog")
def permission_catalog(
    user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    return PermissionService(db).catalog()


@router.post("/households", status_code=201)
def create_household(
    data: HouseholdCreate,
    user: Annotated[AuthUser, Depends(require_scopes(HOUSEHOLD_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    household = service.create_household(data, user)
    return _household_out(household)


@router.get("/households")
def list_households(
    user: Annotated[AuthUser, Depends(require_scopes(HOUSEHOLD_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> list[dict]:
    return [_household_out(item) for item in service.list_for_actor(user)]


@router.get("/households/{household_id}")
def get_household(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(HOUSEHOLD_READ))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    return _household_out(service.get(household_id))


@router.patch("/households/{household_id}")
def update_household(
    household_id: str,
    data: HouseholdUpdate,
    user: Annotated[AuthUser, Depends(require_scopes(HOUSEHOLD_MANAGE))],
    service: Annotated[HouseholdService, Depends(household_service)],
) -> dict:
    service.require_membership(household_id, user)
    PermissionService(service.db).require(household_id, user, "tab.settings", "edit")
    return _household_out(service.update(household_id, data, user))


@router.get("/households/{household_id}/audit")
def list_audit(
    household_id: str,
    user: Annotated[AuthUser, Depends(require_scopes(ADMIN_AUDIT))],
    service: Annotated[HouseholdService, Depends(household_service)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    service.require_membership(household_id, user)
    PermissionService(db).require(household_id, user, "tab.audit", "view")
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.household_id == household_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
    )
    return [
        {
            "id": event.id,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "summary": event.summary,
            "actor_email": event.actor_email,
            "created_at": event.created_at.isoformat(),
        }
        for event in db.scalars(stmt)
    ]


def _household_out(household: Household) -> dict:
    return {
        "id": household.id,
        "name": household.name,
        "household_type": household.household_type,
        "address_line1": household.address_line1,
        "address_line2": household.address_line2,
        "city": household.city,
        "region": household.region,
        "postal_code": household.postal_code,
        "country": household.country,
        "timezone": household.timezone,
        "phone": household.phone,
        "agency_name": household.agency_name,
        "licensing_worker": household.licensing_worker,
        "license_number": household.license_number,
        "capacity": household.capacity,
        "created_at": (
            household.created_at.isoformat() if household.created_at else None
        ),
    }
