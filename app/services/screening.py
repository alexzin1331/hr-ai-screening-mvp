from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import set_candidate_id, set_vacancy_id
from app.core.exceptions import NotFoundError
from app.core.utils import mask_token
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.scoring import Scoring
from app.models.screening_session import ScreeningSession
from app.models.vacancy import Vacancy
from app.repositories.audit_repository import AuditRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.screening_repository import ScreeningRepository
from app.services.email_service import EmailService
from app.services.telegram_service import TelegramService


logger = logging.getLogger(__name__)
SCREENING_QUESTIONS = [
    "Подскажите, пожалуйста, ваш ожидаемый уровень зарплаты.",
    "Какой формат работы вам удобен: офис, гибрид или удалённо?",
    "Какой у вас уровень английского?",
    "Готовы ли вы к интервью в ближайшие 3-5 рабочих дней?",
]
WELCOME_MESSAGE = (
    "Здравствуйте! Ваш invite подтверждён, Telegram подключён. "
    "Я задам несколько коротких вопросов для первичного screening."
)


class ScreeningService:
    def __init__(
        self,
        db: Session,
        telegram_service: TelegramService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self.telegram_service = telegram_service or TelegramService()
        self.email_service = email_service or EmailService()
        self.screening_repo = ScreeningRepository(db)
        self.audit_repo = AuditRepository(db)
        self.candidate_repo = CandidateRepository(db)

    async def start_email_outreach(self, vacancy_id: int, top_n: int, refresh_invite_token: bool = False) -> dict:
        vacancy = self.db.get(Vacancy, vacancy_id)
        if not vacancy:
            raise NotFoundError(f"Vacancy {vacancy_id} not found")
        set_vacancy_id(vacancy_id)

        stmt = (
            select(Candidate, Resume, Scoring)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .join(Scoring, (Scoring.candidate_id == Candidate.id) & (Scoring.vacancy_id == vacancy_id))
            .order_by(Scoring.total_score.desc().nullslast(), Candidate.created_at.desc())
            .limit(top_n)
        )
        rows = self.db.execute(stmt).all()
        details: list[dict[str, Any]] = []
        sent = 0
        email_missing = 0
        invalid_email = 0
        errors = 0

        for candidate, _resume, scoring in rows:
            set_candidate_id(candidate.id)
            logger.info("Email outreach candidate_id=%s vacancy_id=%s score=%s", candidate.id, vacancy_id, scoring.total_score)
            try:
                if refresh_invite_token:
                    self.email_service.ensure_invite_token(candidate, refresh=True)

                result = await self.email_service.send_invite(candidate, vacancy.title)
                if result["status"] == "sent":
                    sent += 1
                elif result["status"] == "email_missing":
                    email_missing += 1
                elif result["status"] == "invalid_email":
                    invalid_email += 1
                elif result["status"] == "failed":
                    errors += 1

                details.append(
                    {
                        "candidate_id": candidate.id,
                        "status": candidate.contact_status,
                        "email": candidate.email,
                        "invite_token": mask_token(candidate.invite_token),
                        "message_id": result.get("message_id"),
                        "error": result.get("error"),
                    }
                )
            except Exception as exc:
                logger.exception("Email outreach failed candidate_id=%s", candidate.id)
                candidate.contact_status = "contact_failed"
                candidate.email_invite_status = "failed"
                candidate.telegram_last_error = str(exc)
                errors += 1
                details.append({"candidate_id": candidate.id, "status": "contact_failed", "error": str(exc)})

        self.audit_repo.log(
            action="start_email_outreach",
            entity_type="vacancy",
            entity_id=str(vacancy_id),
            payload={"top_n": top_n, "sent": sent, "email_missing": email_missing, "invalid_email": invalid_email, "errors": errors},
            message="Запущен email outreach",
        )
        self.db.commit()
        return {
            "requested_top_n": top_n,
            "sent": sent,
            "email_missing": email_missing,
            "invalid_email": invalid_email,
            "errors": errors,
            "details": details,
        }

    async def process_telegram_update(self, update: dict[str, Any]) -> dict[str, Any]:
        message = update.get("message") or {}
        if not message:
            return {"ok": True, "event": "ignored"}

        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        text = (message.get("text") or "").strip()
        chat_id = str(chat.get("id") or "")
        username = from_user.get("username")

        if not chat_id:
            return {"ok": True, "event": "ignored"}

        if text.startswith("/start"):
            token = text.replace("/start", "", 1).strip()
            return await self._handle_start(chat_id=chat_id, username=username, invite_token=token)

        return await self._handle_screening_reply(chat_id=chat_id, text=text, username=username)

    async def send_followup_to_connected_candidates(self, vacancy_id: int, top_n: int, message_template: str | None = None) -> dict:
        vacancy = self.db.get(Vacancy, vacancy_id)
        if not vacancy:
            raise NotFoundError(f"Vacancy {vacancy_id} not found")
        set_vacancy_id(vacancy_id)
        stmt = (
            select(Candidate, Resume, Scoring)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .join(Scoring, (Scoring.candidate_id == Candidate.id) & (Scoring.vacancy_id == vacancy_id))
            .where(Candidate.telegram_chat_id.is_not(None))
            .order_by(Scoring.total_score.desc().nullslast(), Candidate.created_at.desc())
            .limit(top_n)
        )
        rows = self.db.execute(stmt).all()
        details = []
        sent = 0
        errors = 0
        text = message_template or "Напоминаем, что вы можете продолжить screening в этом чате."

        for candidate, _resume, _scoring in rows:
            set_candidate_id(candidate.id)
            try:
                result = await self.telegram_service.send_message(candidate.telegram_chat_id, text)
                sent += 1
                details.append({"candidate_id": candidate.id, "status": "sent", "result": result})
            except Exception as exc:
                logger.exception("Follow-up telegram message failed candidate_id=%s", candidate.id)
                candidate.telegram_last_error = str(exc)
                errors += 1
                details.append({"candidate_id": candidate.id, "status": "failed", "error": str(exc)})

        self.db.commit()
        return {"requested_top_n": top_n, "sent": sent, "skipped_no_telegram": 0, "errors": errors, "details": details}

    async def _handle_start(self, *, chat_id: str, username: str | None, invite_token: str) -> dict[str, Any]:
        masked = mask_token(invite_token)
        logger.info("Received telegram /start token=%s", masked)
        if not invite_token:
            await self.telegram_service.send_message(chat_id, "Ссылка приглашения не содержит токен. Пожалуйста, запросите новое приглашение.")
            return {"ok": True, "event": "start_without_token"}

        candidate = self.candidate_repo.get_by_invite_token(invite_token)
        if not candidate:
            await self.telegram_service.send_message(chat_id, "Токен приглашения не найден. Пожалуйста, запросите новое письмо от HR.")
            return {"ok": True, "event": "invalid_token"}

        set_candidate_id(candidate.id)
        logger.info("candidate_started_telegram candidate_id=%s token=%s", candidate.id, masked)
        if not self._is_token_active(candidate):
            await self.telegram_service.send_message(chat_id, "Срок действия приглашения истёк. Пожалуйста, запросите повторное письмо.")
            return {"ok": True, "event": "expired_token"}

        candidate.telegram_chat_id = chat_id
        candidate.telegram_username = username or candidate.telegram_username
        candidate.telegram_connected_at = datetime.now(timezone.utc)
        candidate.contact_status = "telegram_connected"
        candidate.status = "screening_pending"
        candidate.telegram_last_error = None
        logger.info("telegram_chat_linked candidate_id=%s chat_id=%s", candidate.id, chat_id)

        session = self._get_or_create_session(candidate.id)
        session.status = "screening_in_progress"
        session.last_message_at = datetime.now(timezone.utc).isoformat()
        messages = list(session.messages_json or [])
        messages.append({"direction": "system", "type": "telegram_connected"})
        session.messages_json = messages
        self.audit_repo.log(
            action="telegram_connected",
            entity_type="candidate",
            entity_id=str(candidate.id),
            payload={"invite_token": masked},
            message="Кандидат подтвердил invite через /start",
        )
        self.db.commit()

        await self.telegram_service.send_message(chat_id, WELCOME_MESSAGE)
        await self._ask_next_question(candidate, session)
        return {"ok": True, "event": "telegram_connected"}

    async def _handle_screening_reply(self, *, chat_id: str, text: str, username: str | None) -> dict[str, Any]:
        candidate = self.candidate_repo.get_by_telegram_chat_id(chat_id)
        if not candidate:
            await self.telegram_service.send_message(chat_id, "Чат ещё не привязан к приглашению. Пожалуйста, используйте ссылку из письма.")
            return {"ok": True, "event": "chat_not_linked"}

        set_candidate_id(candidate.id)
        session = self._get_or_create_session(candidate.id)
        messages = list(session.messages_json or [])
        messages.append(
            {
                "direction": "inbound",
                "text": text,
                "username": username,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        session.messages_json = messages
        session.last_message_at = datetime.now(timezone.utc).isoformat()
        candidate.telegram_username = username or candidate.telegram_username
        candidate.contact_status = "screening_in_progress"
        candidate.status = "screening_in_progress"
        self.db.commit()

        await self._ask_next_question(candidate, session)
        return {"ok": True, "event": "screening_progress"}

    async def _ask_next_question(self, candidate: Candidate, session) -> None:
        messages = list(session.messages_json or [])
        answers = [m for m in messages if m.get("direction") == "inbound"]
        if len(answers) >= len(SCREENING_QUESTIONS):
            candidate.contact_status = "screening_completed"
            candidate.status = "screening_completed"
            session.status = "screening_completed"
            self.db.commit()
            await self.telegram_service.send_message(
                candidate.telegram_chat_id,
                "Спасибо! Первичный screening завершён. HR свяжется с вами по следующим шагам.",
            )
            return

        question = SCREENING_QUESTIONS[len(answers)]
        session.status = "screening_in_progress"
        messages.append(
            {
                "direction": "outbound",
                "text": question,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        session.messages_json = messages
        session.last_message_at = datetime.now(timezone.utc).isoformat()
        self.db.commit()
        await self.telegram_service.send_message(candidate.telegram_chat_id, question)

    def _get_or_create_session(self, candidate_id: int):
        session = (
            self.db.execute(
                select(ScreeningSession)
                .where(ScreeningSession.candidate_id == candidate_id)
                .order_by(ScreeningSession.created_at.desc())
            )
            .scalars()
            .first()
        )
        if session:
            return session

        scoring = (
            self.db.execute(
                select(Scoring).where(Scoring.candidate_id == candidate_id).order_by(Scoring.created_at.desc())
            )
            .scalars()
            .first()
        )
        vacancy_id = scoring.vacancy_id if scoring else 0
        return self.screening_repo.create(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            status="pending",
            last_message_at=None,
            messages_json=[],
        )

    def _is_token_active(self, candidate: Candidate) -> bool:
        if not candidate.invite_token_created_at:
            return False
        created_at = candidate.invite_token_created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expires_at = created_at + timedelta(hours=self.settings.invite_token_ttl_hours)
        return expires_at >= datetime.now(timezone.utc)
