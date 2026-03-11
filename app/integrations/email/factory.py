from __future__ import annotations

from app.core.config import get_settings
from app.integrations.email.base import BaseEmailProvider
from app.integrations.email.mock import MockEmailProvider
from app.integrations.email.smtp import SMTPEmailProvider


def get_email_provider() -> BaseEmailProvider:
    settings = get_settings()
    if settings.email_provider == "smtp":
        return SMTPEmailProvider(settings)
    return MockEmailProvider()
