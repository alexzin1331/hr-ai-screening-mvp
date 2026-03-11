from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.concurrency import run_in_threadpool

try:
    import resend
except ImportError:  # pragma: no cover
    resend = None

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationAppError
from app.core.utils import is_valid_email, mask_token
from app.models.candidate import Candidate
from app.utils.tokens import generate_invite_token


logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def ensure_invite_token(self, candidate: Candidate, *, refresh: bool = False) -> str:
        now = datetime.now(timezone.utc)
        ttl = timedelta(hours=self.settings.invite_token_ttl_hours)
        created_at = candidate.invite_token_created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        if refresh or not candidate.invite_token or not created_at or created_at + ttl < now:
            candidate.invite_token = generate_invite_token()
            candidate.invite_token_created_at = now
            logger.info(
                "invite_token_generated candidate_id=%s token=%s",
                candidate.id,
                mask_token(candidate.invite_token),
            )
        return candidate.invite_token

    def build_deep_link(self, invite_token: str) -> str:
        if not self.settings.telegram_bot_username:
            raise ValidationAppError("BOT_USERNAME_MISSING", "Telegram bot username is not configured")
        bot_username = self.settings.telegram_bot_username.lstrip("@")
        return f"https://t.me/{bot_username}?start={invite_token}"

    async def send_invite_email(self, email: str, candidate_name: str, invite_token: str) -> dict[str, Any]:
        deep_link = self.build_deep_link(invite_token)
        subject = "Invitation to AI Screening"
        html = (
            f"<p>Hello {candidate_name or 'candidate'},</p>"
            "<p>Your resume matched our vacancy.</p>"
            "<p>Please start the screening in Telegram:</p>"
            f'<p><a href="{deep_link}">{deep_link}</a></p>'
            "<p>Best regards<br>HR AI Screening</p>"
        )
        logger.info("email_send_attempt email=%s token=%s", email, mask_token(invite_token))

        if self.settings.email_provider == "mock":
            return {
                "success": True,
                "message_id": "mock-message-id",
                "deep_link": deep_link,
            }

        if self.settings.email_provider != "resend":
            return {"success": False, "error": f"Unsupported email provider: {self.settings.email_provider}"}

        if resend is None:
            return {"success": False, "error": "resend package is not installed"}
        if not self.settings.resend_api_key:
            return {"success": False, "error": "RESEND_API_KEY is not configured"}

        resend.api_key = self.settings.resend_api_key
        params = {
            "from": self.settings.resend_email_from,
            "to": [email],
            "subject": subject,
            "html": html,
        }

        try:
            response = await run_in_threadpool(resend.Emails.send, params)
            message_id = self._extract_message_id(response)
            logger.info("email_send_success email=%s message_id=%s", email, message_id)
            return {"success": True, "message_id": message_id, "deep_link": deep_link}
        except Exception as exc:
            logger.exception("email_send_error email=%s", email)
            return {"success": False, "error": str(exc), "deep_link": deep_link}

    async def send_invite(self, candidate: Candidate, company_name: str | None = None) -> dict[str, Any]:
        logger.info("email_extracted candidate_id=%s email=%s", candidate.id, candidate.email)
        if not candidate.email:
            candidate.contact_status = "email_missing"
            candidate.email_invite_status = "missing"
            return {"ok": False, "status": "email_missing"}
        if not is_valid_email(candidate.email):
            candidate.contact_status = "contact_failed"
            candidate.email_invite_status = "invalid"
            return {"ok": False, "status": "invalid_email"}

        token = self.ensure_invite_token(candidate)
        result = await self.send_invite_email(
            email=candidate.email,
            candidate_name=candidate.full_name or "candidate",
            invite_token=token,
        )
        if result["success"]:
            candidate.email_invite_sent_at = datetime.now(timezone.utc)
            candidate.email_invite_status = "sent"
            candidate.contact_status = "awaiting_candidate_start"
            logger.info(
                "email_send_success candidate_id=%s email=%s token=%s",
                candidate.id,
                candidate.email,
                mask_token(candidate.invite_token),
            )
            return {
                "ok": True,
                "status": "sent",
                "deep_link": result["deep_link"],
                "message_id": result["message_id"],
                "company_name": company_name,
            }

        candidate.email_invite_status = "failed"
        candidate.contact_status = "contact_failed"
        candidate.telegram_last_error = result["error"]
        return {"ok": False, "status": "failed", "error": result["error"], "deep_link": result.get("deep_link")}

    @staticmethod
    def _extract_message_id(response: Any) -> str:
        if isinstance(response, dict):
            return str(response.get("id") or response.get("message_id") or "unknown")
        response_dict = getattr(response, "__dict__", {})
        return str(response_dict.get("id") or response_dict.get("message_id") or "unknown")


async def send_invite_email(email: str, candidate_name: str, invite_token: str) -> dict[str, Any]:
    service = EmailService()
    return await service.send_invite_email(email=email, candidate_name=candidate_name, invite_token=invite_token)
