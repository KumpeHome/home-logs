from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth.jwt import InvalidTokenError, JwksTokenValidator
from app.core.auth.management import build_directory
from app.core.auth.scopes import ALL_SCOPES, require_all
from app.core.auth.user import AuthUser
from app.core.config import get_settings
from app.db.session import get_db
from app.services.households import HouseholdService
from app.services.otc import OtcService

bearer = HTTPBearer(auto_error=False)


def get_validator() -> JwksTokenValidator:
    return JwksTokenValidator(get_settings())


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    validator: Annotated[JwksTokenValidator, Depends(get_validator)],
) -> AuthUser:
    settings = get_settings()
    if settings.auth_disabled:
        return AuthUser(
            subject=settings.auth_bypass_subject,
            email=settings.auth_bypass_email,
            name="Dev Admin",
            scopes=ALL_SCOPES,
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return validator.validate(creds.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_scopes(*scopes: str) -> Callable:
    def dependency(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        missing = require_all(user.scopes, scopes)
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing scopes: {', '.join(sorted(missing))}",
            )
        return user

    return dependency


def household_service(
    db: Annotated[Session, Depends(get_db)],
) -> HouseholdService:
    return HouseholdService(db, directory=build_directory(get_settings()))


def otc_service(db: Annotated[Session, Depends(get_db)]) -> OtcService:
    return OtcService(db)


def household_member(
    household_id: Annotated[str, Path()],
    user: Annotated[AuthUser, Depends(get_current_user)],
    service: Annotated[HouseholdService, Depends(household_service)],
):
    return service.require_membership(household_id, user)
