from __future__ import annotations

from collections.abc import Iterable

SCOPE_PREFIX = "homelogs:"
OIDC_IDENTITY_SCOPES = "openid profile email"

HOUSEHOLD_READ = f"{SCOPE_PREFIX}household:read"
HOUSEHOLD_MANAGE = f"{SCOPE_PREFIX}household:manage"
MEMBERS_READ = f"{SCOPE_PREFIX}members:read"
MEMBERS_MANAGE = f"{SCOPE_PREFIX}members:manage"
MEMBERS_INVITE = f"{SCOPE_PREFIX}members:invite"
PROFILES_READ = f"{SCOPE_PREFIX}profiles:read"
PROFILES_WRITE = f"{SCOPE_PREFIX}profiles:write"
LOGS_READ = f"{SCOPE_PREFIX}logs:read"
LOGS_WRITE = f"{SCOPE_PREFIX}logs:write"
LOGS_AMEND = f"{SCOPE_PREFIX}logs:amend"
LOGS_EXPORT = f"{SCOPE_PREFIX}logs:export"
FORMS_MANAGE_TEMPLATES = f"{SCOPE_PREFIX}forms:managetemplates"
EDUCATION_READ = f"{SCOPE_PREFIX}education:read"
EDUCATION_WRITE = f"{SCOPE_PREFIX}education:write"
DISCIPLINE_READ = f"{SCOPE_PREFIX}discipline:read"
DISCIPLINE_WRITE = f"{SCOPE_PREFIX}discipline:write"
DOCUMENTS_READ = f"{SCOPE_PREFIX}documents:read"
DOCUMENTS_WRITE = f"{SCOPE_PREFIX}documents:write"
ADMIN_AUDIT = f"{SCOPE_PREFIX}admin:audit"

ALL_SCOPES: frozenset[str] = frozenset(
    {
        HOUSEHOLD_READ,
        HOUSEHOLD_MANAGE,
        MEMBERS_READ,
        MEMBERS_MANAGE,
        MEMBERS_INVITE,
        PROFILES_READ,
        PROFILES_WRITE,
        LOGS_READ,
        LOGS_WRITE,
        LOGS_AMEND,
        LOGS_EXPORT,
        FORMS_MANAGE_TEMPLATES,
        EDUCATION_READ,
        EDUCATION_WRITE,
        DISCIPLINE_READ,
        DISCIPLINE_WRITE,
        DOCUMENTS_READ,
        DOCUMENTS_WRITE,
        ADMIN_AUDIT,
    }
)


def _normalize_scope_token(token: str) -> str | None:
    normalized = token.lower()
    if normalized.startswith(SCOPE_PREFIX) and "." not in normalized:
        return normalized
    return None


def parse_homelogs_scopes(claim: str | Iterable[str] | None) -> frozenset[str]:
    if claim is None:
        return frozenset()
    tokens = claim.split() if isinstance(claim, str) else list(claim)
    return frozenset(filter(None, (_normalize_scope_token(token) for token in tokens)))


def require_all(have: frozenset[str], needed: Iterable[str]) -> frozenset[str]:
    return frozenset(needed) - have


def oidc_requested_scopes(identity_scopes: str = OIDC_IDENTITY_SCOPES) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for token in [*identity_scopes.split(), *sorted(ALL_SCOPES)]:
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)
    return " ".join(tokens)
