from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


class _FakeResponse:
    def __init__(
        self, status_code: int, payload: dict | None = None, text: str = ""
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def test_auth_token_exchanges_code_with_idp(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("OIDC_ISSUER", "https://auth.stage.kumpe.app")
    monkeypatch.setenv("OIDC_CLIENT_ID", "home-logs-spa")
    monkeypatch.setenv("OIDC_AUDIENCE", "https://homelogs.app/api")
    get_settings.cache_clear()
    captured: dict = {}

    def fake_post(url: str, data=None, timeout=None, **_kwargs):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse(200, {"access_token": "tok-1", "scope": "openid"})

    monkeypatch.setattr("app.core.auth.token.httpx.post", fake_post)
    with TestClient(create_app(init_db=False)) as client:
        response = client.post(
            "/api/auth/token",
            json={
                "code": "abc",
                "code_verifier": "verifier",
                "redirect_uri": "https://homelogs.stage.kumpe.app/callback",
            },
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "tok-1"
    assert captured["url"] == "https://auth.stage.kumpe.app/oidc/token"
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["code"] == "abc"
    assert captured["data"]["resource"] == "https://homelogs.app/api"
    get_settings.cache_clear()


def test_auth_token_uses_client_resource_when_provided(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("OIDC_ISSUER", "https://auth.stage.kumpe.app")
    monkeypatch.setenv("OIDC_CLIENT_ID", "home-logs-spa")
    monkeypatch.setenv("OIDC_AUDIENCE", "https://homelogs.app/api")
    get_settings.cache_clear()
    captured: dict = {}

    def fake_post(url: str, data=None, timeout=None, **_kwargs):
        captured["data"] = data
        return _FakeResponse(200, {"access_token": "tok-2"})

    monkeypatch.setattr("app.core.auth.token.httpx.post", fake_post)
    with TestClient(create_app(init_db=False)) as client:
        response = client.post(
            "/api/auth/token",
            json={
                "code": "abc",
                "code_verifier": "verifier",
                "redirect_uri": "https://homelogs.stage.kumpe.app/callback",
                "resource": "https://homelogs.kumpe.app",
            },
        )
    assert response.status_code == 200
    assert captured["data"]["resource"] == "https://homelogs.kumpe.app"
    get_settings.cache_clear()


def test_auth_token_returns_400_when_idp_rejects(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("OIDC_ISSUER", "https://auth.stage.kumpe.app")
    monkeypatch.setenv("OIDC_CLIENT_ID", "home-logs-spa")
    monkeypatch.setenv("OIDC_AUDIENCE", "https://homelogs.app/api")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.core.auth.token.httpx.post",
        lambda *args, **kwargs: _FakeResponse(400, text="invalid_grant"),
    )
    with TestClient(create_app(init_db=False)) as client:
        response = client.post(
            "/api/auth/token",
            json={
                "code": "bad",
                "code_verifier": "verifier",
                "redirect_uri": "https://homelogs.stage.kumpe.app/callback",
            },
        )
    assert response.status_code == 400
    get_settings.cache_clear()
