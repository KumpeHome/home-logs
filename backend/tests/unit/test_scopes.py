from app.core.auth.scopes import (
    ALL_SCOPES,
    FORMS_MANAGE_TEMPLATES,
    HOUSEHOLD_READ,
    SCOPE_PREFIX,
    oidc_requested_scopes,
    parse_homelogs_scopes,
    require_all,
)


def test_rbac_scopes_are_lowercase_colon_separated() -> None:
    assert SCOPE_PREFIX == "homelogs:"
    assert HOUSEHOLD_READ == "homelogs:household:read"
    assert FORMS_MANAGE_TEMPLATES == "homelogs:forms:managetemplates"
    assert all(scope == scope.lower() for scope in ALL_SCOPES)
    assert all("." not in scope for scope in ALL_SCOPES)
    assert all(scope.startswith(SCOPE_PREFIX) for scope in ALL_SCOPES)


def test_parse_keeps_only_homelogs_prefixed_scopes() -> None:
    raw = "openid profile homelogs:logs:read email homelogs:logs:write"
    assert parse_homelogs_scopes(raw) == frozenset(
        {"homelogs:logs:read", "homelogs:logs:write"}
    )


def test_parse_normalizes_scope_case() -> None:
    assert parse_homelogs_scopes("openid HomeLogs:Logs.Read") == frozenset()
    assert parse_homelogs_scopes("openid HOMELOGS:LOGS:READ") == frozenset(
        {"homelogs:logs:read"}
    )


def test_parse_accepts_list_claim() -> None:
    assert parse_homelogs_scopes(["homelogs:members:read", "offline_access"]) == (
        frozenset({"homelogs:members:read"})
    )


def test_require_all_returns_missing_scopes() -> None:
    have = frozenset({f"{SCOPE_PREFIX}logs:read"})
    missing = require_all(
        have, [f"{SCOPE_PREFIX}logs:read", f"{SCOPE_PREFIX}logs:write"]
    )
    assert missing == frozenset({f"{SCOPE_PREFIX}logs:write"})


def test_empty_scope_claim_is_empty_set() -> None:
    assert parse_homelogs_scopes(None) == frozenset()
    assert parse_homelogs_scopes("") == frozenset()


def test_oidc_requested_scopes_include_identity_and_rbac() -> None:
    requested = oidc_requested_scopes("openid profile email").split()
    assert requested[:3] == ["openid", "profile", "email"]
    assert set(ALL_SCOPES).issubset(set(requested))
