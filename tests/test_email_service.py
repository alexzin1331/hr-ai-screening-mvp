from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_invite_email_success_with_resend_mock(monkeypatch):
    settings = get_settings()
    settings.email_provider = "resend"
    settings.resend_api_key = "resend_test_key"
    settings.resend_email_from = "HR AI Screening <onboarding@resend.dev>"
    settings.telegram_bot_username = "test_bot"

    captured = {}

    def fake_send(params):
        captured["params"] = params
        return {"id": "email_123"}

    monkeypatch.setattr(
        "app.services.email_service.resend",
        type("ResendModule", (), {"Emails": type("Emails", (), {"send": staticmethod(fake_send)})})(),
    )

    service = EmailService(settings=settings)
    result = await service.send_invite_email(
        email="candidate@example.com",
        candidate_name="Ivan",
        invite_token="token123",
    )

    assert result["success"] is True
    assert result["message_id"] == "email_123"
    assert "https://t.me/test_bot?start=token123" in result["deep_link"]
    assert captured["params"]["to"] == ["candidate@example.com"]
    assert captured["params"]["subject"] == "Invitation to AI Screening"


@pytest.mark.asyncio
async def test_send_invite_email_failure_with_resend_mock(monkeypatch):
    settings = get_settings()
    settings.email_provider = "resend"
    settings.resend_api_key = "resend_test_key"
    settings.resend_email_from = "HR AI Screening <onboarding@resend.dev>"
    settings.telegram_bot_username = "test_bot"

    def fake_send(_params):
        raise RuntimeError("resend failed")

    monkeypatch.setattr(
        "app.services.email_service.resend",
        type("ResendModule", (), {"Emails": type("Emails", (), {"send": staticmethod(fake_send)})})(),
    )

    service = EmailService(settings=settings)
    result = await service.send_invite_email(
        email="candidate@example.com",
        candidate_name="Ivan",
        invite_token="token123",
    )

    assert result["success"] is False
    assert "resend failed" in result["error"]
