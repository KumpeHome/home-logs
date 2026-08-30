def oidc_origin(issuer: str) -> str:
    base = issuer.rstrip("/")
    if base.endswith("/oidc"):
        return base[: -len("/oidc")]
    return base


def oidc_issuer_aliases(issuer: str) -> list[str]:
    origin = oidc_origin(issuer)
    return [origin, f"{origin}/oidc"]


def oidc_token_url(issuer: str) -> str:
    return f"{oidc_origin(issuer)}/oidc/token"


def oidc_jwks_url(issuer: str) -> str:
    return f"{oidc_origin(issuer)}/oidc/jwks"
