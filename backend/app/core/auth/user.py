from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.auth.scopes import parse_homelogs_scopes


@dataclass(frozen=True)
class AuthUser:
    subject: str
    email: str | None
    scopes: frozenset[str]
    name: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


class TokenValidator(Protocol):
    def validate(self, token: str) -> AuthUser: ...


def auth_user_from_claims(claims: dict[str, Any]) -> AuthUser:
    scope_claim = claims.get("scope") or claims.get("scp") or claims.get("permissions")
    return AuthUser(
        subject=str(claims.get("sub") or ""),
        email=claims.get("email") or claims.get("username"),
        name=claims.get("name"),
        scopes=parse_homelogs_scopes(scope_claim),
        claims=claims,
    )
