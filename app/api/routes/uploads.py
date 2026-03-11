from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.context import set_vacancy_id
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.repositories.vacancy_repository import VacancyRepository
from app.schemas.resume import UploadSummary
from app.services.pipeline import ResumeProcessingPipeline


logger = logging.getLogger(__name__)
router = APIRouter(tags=["uploads"])
legacy_router = APIRouter(tags=["legacy"])


@router.post("/vacancies/{vacancy_id}/resumes", response_model=UploadSummary)
async def upload_resumes(
    vacancy_id: int,
    file: UploadFile = File(...),
    consent_to_personal_data_processing: bool = Form(default=True),
    db: Session = Depends(get_db),
) -> UploadSummary:
    vacancy = VacancyRepository(db).get(vacancy_id)
    if not vacancy:
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    set_vacancy_id(vacancy_id)
    logger.info("Upload started vacancy_id=%s filename=%s", vacancy_id, file.filename)
    pipeline = ResumeProcessingPipeline(db)
    result = await pipeline.process_upload(
        vacancy,
        file,
        consent_to_personal_data_processing=consent_to_personal_data_processing,
    )
    return UploadSummary.model_validate(result)


@router.post("/vacancies/{vacancy_id}/resumes/upload", response_model=UploadSummary)
async def upload_resumes_explicit(
    vacancy_id: int,
    file: UploadFile = File(...),
    consent_to_personal_data_processing: bool = Form(default=True),
    db: Session = Depends(get_db),
) -> UploadSummary:
    return await upload_resumes(
        vacancy_id=vacancy_id,
        file=file,
        consent_to_personal_data_processing=consent_to_personal_data_processing,
        db=db,
    )


@router.post("/upload_resumes", response_model=UploadSummary)
async def upload_resumes_legacy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadSummary:
    vacancy = VacancyRepository(db).list()
    latest = vacancy[0] if vacancy else None
    if not latest:
        raise NotFoundError("No vacancy found. Create vacancy first.")
    pipeline = ResumeProcessingPipeline(db)
    result = await pipeline.process_upload(latest, file, consent_to_personal_data_processing=True)
    return UploadSummary.model_validate(result)


@legacy_router.post("/upload_resumes", response_model=UploadSummary)
async def upload_resumes_root(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadSummary:
    return await upload_resumes_legacy(file=file, db=db)
