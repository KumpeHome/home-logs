from __future__ import annotations

from typing import Protocol

import httpx

from app.core.auth.oidc_urls import oidc_token_url
from app.core.config import Settings


class IdentityDirectory(Protocol):
    def invite(self, email: str, role: str | None) -> dict: ...


class NoOpDirectory:
    def invite(self, email: str, role: str | None) -> dict:
        return {"status": "local_only", "email": email, "role": role}


class LogtoCompatibleDirectory:
    """Invites users through Logto-compatible Management API (KumpeCloud Auth)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def invite(self, email: str, role: str | None) -> dict:
        if not (
            self._settings.oidc_m2m_client_id
            and self._settings.oidc_m2m_client_secret
            and self._settings.oidc_management_api
        ):
            return NoOpDirectory().invite(email, role)
        token = self._m2m_token()
        base = self._settings.oidc_management_api.rstrip("/")
        payload = {
            "primaryEmail": email,
            "username": email.split("@")[0],
            "name": email,
        }
        if role:
            payload["customData"] = {"homeLogsRole": role}
        response = httpx.post(
            f"{base}/users",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=20,
        )
        if response.status_code >= 400:
            return {
                "status": "idp_error",
                "detail": response.text,
                "email": email,
            }
        return {"status": "invited", "email": email, "idp": response.json()}

    def _m2m_token(self) -> str:
        response = httpx.post(
            oidc_token_url(self._settings.oidc_issuer),
            data={
                "grant_type": "client_credentials",
                "client_id": self._settings.oidc_m2m_client_id,
                "client_secret": self._settings.oidc_m2m_client_secret,
                "resource": self._settings.oidc_management_api,
                "scope": "all",
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]


def build_directory(settings: Settings) -> IdentityDirectory:
    if (
        settings.oidc_m2m_client_id
        and settings.oidc_m2m_client_secret
        and settings.oidc_management_api
    ):
        return LogtoCompatibleDirectory(settings)
    return NoOpDirectory()
