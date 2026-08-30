from fastapi.testclient import TestClient

from app.core.auth.scopes import ALL_SCOPES, HOUSEHOLD_MANAGE
from app.core.config import get_settings
from app.main import create_app


def test_health_reports_auth_bypass_off_by_default(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    with TestClient(create_app(init_db=False)) as client:
        body = client.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["auth_bypass"] is False


def test_health_reports_auth_bypass_when_auth_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    with TestClient(create_app(init_db=False)) as client:
        body = client.get("/api/health").json()
        assert body["auth_bypass"] is True
    get_settings.cache_clear()


def test_oidc_required_when_auth_not_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    with TestClient(create_app(init_db=False)) as client:
        response = client.get("/api/me")
        assert response.status_code == 401


def test_auth_disabled_allows_me_without_jwt(monkeypatch, sqlite_engine) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.db.session import get_db

    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("AUTH_BYPASS_EMAIL", "dev@homelogs.local")
    monkeypatch.setenv("AUTH_BYPASS_SUBJECT", "dev-bypass")
    get_settings.cache_clear()

    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)

    def override_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    application = create_app(init_db=False)
    application.dependency_overrides[get_db] = override_db
    with TestClient(application) as client:
        response = client.get("/api/me")
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "dev@homelogs.local"
        assert body["subject"] == "dev-bypass"
        assert HOUSEHOLD_MANAGE in body["scopes"]
        assert set(ALL_SCOPES).issubset(set(body["scopes"]))
    get_settings.cache_clear()
