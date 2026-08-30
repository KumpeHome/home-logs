from app.core.auth.jwt import StaticKeyValidator
from app.core.auth.scopes import ALL_SCOPES, HOUSEHOLD_MANAGE
from app.core.auth.user import auth_user_from_claims


def test_auth_user_from_claims_filters_homelogs_scopes() -> None:
    user = auth_user_from_claims(
        {
            "sub": "user-1",
            "email": "ada@example.com",
            "scope": "openid homelogs:household:manage profile",
        }
    )
    assert user.subject == "user-1"
    assert user.scopes == frozenset({HOUSEHOLD_MANAGE})


def test_static_validator_round_trip_rs256() -> None:
    from datetime import UTC, datetime, timedelta

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key()
    token = jwt.encode(
        {
            "sub": "sub-9",
            "email": "nine@example.com",
            "aud": "https://homelogs.app/api",
            "iss": "http://auth.test",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "scope": "homelogs:logs:read",
        },
        key,
        algorithm="RS256",
    )
    validator = StaticKeyValidator(
        public, issuer="http://auth.test", audience="https://homelogs.app/api"
    )
    user = validator.validate(token)
    assert user.subject == "sub-9"
    assert "homelogs:logs:read" in user.scopes
    assert HOUSEHOLD_MANAGE not in user.scopes
    assert len(ALL_SCOPES) >= 10
