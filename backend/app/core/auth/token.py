from __future__ import annotations

import httpx
from fastapi import HTTPException

from app.core.auth.oidc_urls import oidc_token_url
from app.core.config import Settings


def exchange_authorization_code(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.oidc_client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "resource": settings.oidc_audience,
    }
    if settings.oidc_client_secret:
        data["client_secret"] = settings.oidc_client_secret
    response = httpx.post(oidc_token_url(settings.oidc_issuer), data=data, timeout=20)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=400, detail=response.text or "token exchange failed"
        )
    payload = response.json()
    if not payload.get("access_token"):
        raise HTTPException(
            status_code=400, detail="token exchange returned no access_token"
        )
    return payload
