from __future__ import annotations

from pydantic import BaseModel, Field


class SubscriptionIn(BaseModel):
    topic: str
    subject_member_id: str | None = None


class NotificationSettingsIn(BaseModel):
    member_id: str
    email_enabled: bool = False
    pushover_enabled: bool = False
    pushover_user_key: str | None = None
    dose_lead_minutes: int = Field(default=15, ge=0, le=180)
    dose_window_before_minutes: int = Field(default=30, ge=0, le=240)
    dose_window_after_minutes: int = Field(default=60, ge=0, le=240)
    dose_repeat_count: int = Field(default=1, ge=1, le=10)
    dose_repeat_interval_minutes: int = Field(default=15, ge=0, le=180)
    subscriptions: list[SubscriptionIn] = Field(default_factory=list)


class PushoverStartIn(BaseModel):
    member_id: str


class NotificationTestIn(BaseModel):
    member_id: str


class PushoverCompleteIn(BaseModel):
    member_id: str
    rand: str
    pushover_user_key: str | None = None
    pushover_unsubscribed: bool = False
