from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.vacancy import Vacancy
from app.schemas.screening import (
    EmailOutreachRequest,
    EmailOutreachResponse,
    LegacyOutreachRequest,
    OutreachRequest,
    OutreachResponse,
    TelegramWebhookResponse,
)
from app.services.screening import ScreeningService


router = APIRouter(tags=["screening"])
legacy_router = APIRouter(tags=["legacy"])


@router.post("/vacancies/{vacancy_id}/outreach", response_model=OutreachResponse)
async def start_outreach(
    vacancy_id: int,
    payload: OutreachRequest,
    db: Session = Depends(get_db),
) -> OutreachResponse:
    if not db.get(Vacancy, vacancy_id):
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    service = ScreeningService(db)
    result = await service.send_followup_to_connected_candidates(vacancy_id, payload.top_n, payload.message_template)
    return OutreachResponse.model_validate(result)


@router.post("/vacancies/{vacancy_id}/email-outreach", response_model=EmailOutreachResponse)
async def start_email_outreach(
    vacancy_id: int,
    payload: EmailOutreachRequest,
    db: Session = Depends(get_db),
) -> EmailOutreachResponse:
    if not db.get(Vacancy, vacancy_id):
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    service = ScreeningService(db)
    result = await service.start_email_outreach(vacancy_id, payload.top_n, payload.refresh_invite_token)
    return EmailOutreachResponse.model_validate(result)


@router.post("/vacancies/{vacancy_id}/send-invites", response_model=EmailOutreachResponse)
async def send_invites(
    vacancy_id: int,
    payload: EmailOutreachRequest,
    db: Session = Depends(get_db),
) -> EmailOutreachResponse:
    return await start_email_outreach(vacancy_id=vacancy_id, payload=payload, db=db)


@router.post("/start_screening", response_model=OutreachResponse)
async def start_outreach_legacy(payload: LegacyOutreachRequest, db: Session = Depends(get_db)) -> OutreachResponse:
    vacancy = db.execute(select(Vacancy).order_by(Vacancy.created_at.desc())).scalars().first()
    if not vacancy:
        raise NotFoundError("No vacancy found. Create vacancy first.")
    service = ScreeningService(db)
    result = await service.start_email_outreach(vacancy.id, payload.n, False)
    return OutreachResponse.model_validate(
        {
            "requested_top_n": result["requested_top_n"],
            "sent": result["sent"],
            "skipped_no_telegram": result["email_missing"] + result["invalid_email"],
            "errors": result["errors"],
            "details": result["details"],
        }
    )


@legacy_router.post("/start_screening", response_model=OutreachResponse)
async def start_outreach_root(payload: LegacyOutreachRequest, db: Session = Depends(get_db)) -> OutreachResponse:
    return await start_outreach_legacy(payload=payload, db=db)


@router.post("/telegram/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(request: Request, db: Session = Depends(get_db)) -> TelegramWebhookResponse:
    payload = await request.json()
    service = ScreeningService(db)
    result = await service.process_telegram_update(payload)
    return TelegramWebhookResponse.model_validate(result)


@legacy_router.post("/telegram/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook_root(request: Request, db: Session = Depends(get_db)) -> TelegramWebhookResponse:
    return await telegram_webhook(request=request, db=db)
