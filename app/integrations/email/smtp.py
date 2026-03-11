from __future__ import annotations

import smtplib
from email.message import EmailMessage

from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings
from app.integrations.email.base import BaseEmailProvider


class SMTPEmailProvider(BaseEmailProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_email(self, to_email: str, subject: str, body: str) -> dict:
        await run_in_threadpool(self._send_sync, to_email, subject, body)
        return {"ok": True, "provider": "smtp", "to_email": to_email}

    def _send_sync(self, to_email: str, subject: str, body: str) -> None:
        if not self.settings.smtp_host:
            raise ValueError("SMTP host is not configured")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.settings.email_from_name} <{self.settings.email_from_address}>"
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.send_message(message)
