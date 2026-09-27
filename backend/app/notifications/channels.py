from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.errors import DomainError

PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_MIGRATE_URL = "https://api.pushover.net/1/subscriptions/migrate.json"


class DeliveryChannel(Protocol):
    code: str

    def deliver(self, *, destination: str, title: str, body: str) -> None: ...


class EmailChannel:
    code = "email"

    def __init__(self, settings) -> None:
        self._settings = settings

    def deliver(self, *, destination: str, title: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = destination
        message["Subject"] = title
        message.set_content(body)
        with smtplib.SMTP(
            self._settings.smtp_host, self._settings.smtp_port, timeout=20
        ) as smtp:
            if self._settings.smtp_starttls:
                smtp.starttls()
            if self._settings.smtp_username:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(message)


class PushoverChannel:
    code = "pushover"

    def __init__(self, api_token: str) -> None:
        self._api_token = api_token

    def deliver(self, *, destination: str, title: str, body: str) -> None:
        send_pushover_message(
            token=self._api_token, user_key=destination, title=title, message=body
        )


def build_channels(settings) -> dict[str, DeliveryChannel]:
    channels: dict[str, DeliveryChannel] = {}
    if settings.smtp_host.strip() and settings.smtp_from.strip():
        channels["email"] = EmailChannel(settings)
    if settings.pushover_api_token.strip():
        channels["pushover"] = PushoverChannel(settings.pushover_api_token.strip())
    return channels


def send_pushover_message(
    *, token: str, user_key: str, title: str, message: str
) -> None:
    with httpx.Client(timeout=20) as client:
        response = client.post(
            PUSHOVER_MESSAGES_URL,
            data={
                "token": token,
                "user": user_key,
                "title": title,
                "message": message,
            },
        )
    if response.status_code >= 400 or response.json().get("status") != 1:
        raise RuntimeError("Pushover rejected the message")


def migrate_pushover_user_key(*, token: str, subscription: str, user_key: str) -> str:
    with httpx.Client(timeout=20) as client:
        response = client.post(
            PUSHOVER_MIGRATE_URL,
            data={"token": token, "subscription": subscription, "user": user_key},
        )
    if response.status_code >= 400:
        raise DomainError("Pushover could not subscribe that user key")
    payload = response.json()
    subscribed = payload.get("subscribed_user_key")
    if payload.get("status") != 1 or not subscribed:
        raise DomainError("Pushover could not subscribe that user key")
    return str(subscribed)
