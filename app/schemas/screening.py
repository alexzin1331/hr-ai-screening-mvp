from __future__ import annotations

from pydantic import BaseModel, Field


class OutreachRequest(BaseModel):
    top_n: int = Field(gt=0, le=100)
    message_template: str | None = None


class LegacyOutreachRequest(BaseModel):
    n: int = Field(gt=0, le=100)


class OutreachResponse(BaseModel):
    requested_top_n: int
    sent: int
    skipped_no_telegram: int
    errors: int
    details: list[dict]


class EmailOutreachRequest(BaseModel):
    top_n: int = Field(gt=0, le=100)
    refresh_invite_token: bool = False


class EmailOutreachResponse(BaseModel):
    requested_top_n: int
    sent: int
    email_missing: int
    invalid_email: int
    errors: int
    details: list[dict]


class TelegramWebhookResponse(BaseModel):
    ok: bool
    event: str
