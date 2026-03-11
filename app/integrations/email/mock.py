from __future__ import annotations

from datetime import datetime, timezone

from app.integrations.email.base import BaseEmailProvider


class MockEmailProvider(BaseEmailProvider):
    async def send_email(self, to_email: str, subject: str, body: str) -> dict:
        return {
            "ok": True,
            "dry_run": True,
            "to_email": to_email,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "body_preview": body[:160],
        }
