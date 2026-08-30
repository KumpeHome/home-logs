from __future__ import annotations

import jwt
from jwt import PyJWKClient

from app.core.auth.oidc_urls import oidc_issuer_aliases, oidc_jwks_url
from app.core.auth.user import AuthUser, auth_user_from_claims
from app.core.config import Settings

_JWT_ALGS = ["RS256", "RS384", "ES256", "ES384"]


class InvalidTokenError(Exception):
    pass


def _audience_values(aud: object) -> list[str]:
    if isinstance(aud, str):
        return [aud]
    if isinstance(aud, (list, tuple)):
        return [str(item) for item in aud]
    return []


def _audience_allowed(aud: object, allowed: list[str]) -> bool:
    return any(value in allowed for value in _audience_values(aud))


def decode_access_token(
    token: str,
    key,
    issuer: str,
    audience: str,
    extra_audiences: tuple[str, ...] = (),
) -> dict:
    issuers = oidc_issuer_aliases(issuer)
    allowed = [item for item in (audience, *extra_audiences) if item]
    try:
        return jwt.decode(
            token,
            key,
            algorithms=_JWT_ALGS,
            audience=allowed,
            issuer=issuers,
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidAudienceError as aud_exc:
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=_JWT_ALGS,
                issuer=issuers,
                options={"require": ["sub", "exp"], "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        aud = claims.get("aud")
        if _audience_allowed(aud, allowed):
            return claims
        raise InvalidTokenError(
            f"audience mismatch (token={aud!r} expected={allowed!r})"
        ) from aud_exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


class JwksTokenValidator:
    def __init__(self, settings: Settings) -> None:
        jwks_url = settings.oidc_jwks_url or oidc_jwks_url(settings.oidc_issuer)
        self._issuer = settings.oidc_issuer
        self._audience = settings.oidc_audience
        self._extra_audiences = tuple(
            item for item in (settings.oidc_client_id,) if item
        )
        self._client = PyJWKClient(jwks_url)

    def validate(self, token: str) -> AuthUser:
        try:
            key = self._client.get_signing_key_from_jwt(token).key
        except Exception as exc:
            raise InvalidTokenError("unable to load signing key") from exc
        claims = decode_access_token(
            token,
            key,
            self._issuer,
            self._audience,
            extra_audiences=self._extra_audiences,
        )
        user = auth_user_from_claims(claims)
        if not user.subject:
            raise InvalidTokenError("missing sub")
        return user


class StaticKeyValidator:
    def __init__(
        self,
        public_key,
        issuer: str,
        audience: str,
        extra_audiences: tuple[str, ...] = (),
    ) -> None:
        self._public_key = public_key
        self._issuer = issuer
        self._audience = audience
        self._extra_audiences = extra_audiences

    def validate(self, token: str) -> AuthUser:
        claims = decode_access_token(
            token,
            self._public_key,
            self._issuer,
            self._audience,
            extra_audiences=self._extra_audiences,
        )
        return auth_user_from_claims(claims)
