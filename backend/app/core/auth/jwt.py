from __future__ import annotations

import jwt
from jwt import PyJWKClient

from app.core.auth.oidc_urls import oidc_issuer_aliases, oidc_jwks_url
from app.core.auth.user import AuthUser, auth_user_from_claims
from app.core.config import Settings


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str, key, issuer: str, audience: str) -> dict:
    issuers = oidc_issuer_aliases(issuer)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=issuers,
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidAudienceError as aud_exc:
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256"],
                issuer=issuers,
                options={"require": ["sub", "exp"], "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        aud = claims.get("aud")
        if aud != audience and not (isinstance(aud, list) and audience in aud):
            raise InvalidTokenError("audience mismatch") from aud_exc
        return claims
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


class JwksTokenValidator:
    def __init__(self, settings: Settings) -> None:
        jwks_url = settings.oidc_jwks_url or oidc_jwks_url(settings.oidc_issuer)
        self._issuer = settings.oidc_issuer
        self._audience = settings.oidc_audience
        self._client = PyJWKClient(jwks_url)

    def validate(self, token: str) -> AuthUser:
        try:
            key = self._client.get_signing_key_from_jwt(token).key
        except Exception as exc:
            raise InvalidTokenError("unable to load signing key") from exc
        claims = decode_access_token(token, key, self._issuer, self._audience)
        user = auth_user_from_claims(claims)
        if not user.subject:
            raise InvalidTokenError("missing sub")
        return user


class StaticKeyValidator:
    def __init__(self, public_key, issuer: str, audience: str) -> None:
        self._public_key = public_key
        self._issuer = issuer
        self._audience = audience

    def validate(self, token: str) -> AuthUser:
        claims = decode_access_token(
            token, self._public_key, self._issuer, self._audience
        )
        return auth_user_from_claims(claims)
