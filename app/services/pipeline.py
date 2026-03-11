from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import set_candidate_id, set_resume_id, set_vacancy_id
from app.models.candidate import Candidate
from app.models.vacancy import Vacancy
from app.db.session import SessionLocal
from app.repositories.audit_repository import AuditRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.scoring_repository import ScoringRepository
from app.schemas.candidate import CandidateProfile
from app.services.candidate_extractor import CandidateExtractorService
from app.services.file_service import FileService, StoredFile
from app.services.resume_parser import ResumeParserService
from app.services.scoring import ScoringService


logger = logging.getLogger(__name__)


class ResumeProcessingPipeline:
    def __init__(
        self,
        db: Session,
        file_service: FileService | None = None,
        parser: ResumeParserService | None = None,
        extractor: CandidateExtractorService | None = None,
        scoring_service: ScoringService | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self.file_service = file_service or FileService()
        self.parser = parser or ResumeParserService()
        self.extractor = extractor or CandidateExtractorService()
        self.scoring_service = scoring_service or ScoringService()
        self.audit_repo = AuditRepository(db)
        self.candidate_repo = CandidateRepository(db)
        self.resume_repo = ResumeRepository(db)
        self.scoring_repo = ScoringRepository(db)
        self.processing_semaphore = asyncio.Semaphore(self.settings.processing_concurrency_limit)

    async def process_upload(
        self,
        vacancy: Vacancy,
        upload,
        *,
        consent_to_personal_data_processing: bool,
    ) -> dict:
        set_vacancy_id(vacancy.id)
        saved = self.file_service.save_upload(upload)
        files = self.file_service.collect_resume_files(saved)
        batch_id = str(uuid.uuid4())
        self.audit_repo.log(
            action="upload_resumes",
            entity_type="vacancy",
            entity_id=str(vacancy.id),
            payload={"file_name": saved.original_name, "file_count": len(files), "batch_id": batch_id},
            message="Загружены резюме",
        )
        self.db.commit()

        tasks = [
            self._process_single_file(vacancy.id, stored_file, consent_to_personal_data_processing)
            for stored_file in files
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        summary = {
            "batch_id": batch_id,
            "vacancy_id": vacancy.id,
            "processed": sum(1 for item in results if item["status"] == "processed"),
            "created_candidates": sum(1 for item in results if item.get("candidate_id")),
            "parse_failed": sum(1 for item in results if item["status"] == "parse_failed"),
            "skipped_unsupported": self.file_service.last_skipped_unsupported,
            "skipped_empty": sum(1 for item in results if item["status"] == "empty"),
            "skipped_errors": sum(1 for item in results if item["status"] == "error"),
            "files": results,
        }
        logger.info("Resume batch processing finished batch_id=%s summary=%s", batch_id, summary)
        return summary

    async def _process_single_file(
        self,
        vacancy_id: int,
        stored_file: StoredFile,
        consent_to_personal_data_processing: bool,
    ) -> dict:
        async with self.processing_semaphore:
            logger.info("Processing resume file original=%s path=%s", stored_file.original_name, stored_file.path)
            raw_text = None
            with SessionLocal() as task_db:
                vacancy = task_db.get(Vacancy, vacancy_id)
                candidate_repo = CandidateRepository(task_db)
                resume_repo = ResumeRepository(task_db)
                scoring_repo = ScoringRepository(task_db)

                candidate = candidate_repo.create(
                    full_name=None,
                    email=None,
                    phone=None,
                    location=None,
                    telegram_username=None,
                    telegram_chat_id=None,
                    telegram_connected_at=None,
                    contact_status="new",
                    invite_token=None,
                    invite_token_created_at=None,
                    email_invite_sent_at=None,
                    email_invite_status=None,
                    telegram_last_error=None,
                    source="upload",
                    status="processing",
                    consent_to_personal_data_processing=consent_to_personal_data_processing,
                )
                task_db.flush()
                set_candidate_id(candidate.id)

                resume = resume_repo.create(
                    candidate_id=candidate.id,
                    file_name=stored_file.original_name,
                    file_type=stored_file.file_type,
                    raw_text=None,
                    parsed_json=None,
                    parse_status="processing",
                    parse_error=None,
                    storage_path=str(stored_file.path),
                )
                task_db.commit()
                set_resume_id(resume.id)

                try:
                    raw_text = await run_in_threadpool(self.parser.parse_resume, stored_file.path)
                    profile = await self.extractor.extract(raw_text)
                    score = await self.scoring_service.score(vacancy, profile)

                    resume = task_db.get(type(resume), resume.id)
                    candidate = task_db.get(type(candidate), candidate.id)
                    resume.raw_text = raw_text
                    resume.parsed_json = profile.model_dump(mode="json")
                    resume.parse_status = "parsed"
                    self._apply_candidate_profile(candidate, profile)
                    candidate.status = "parsed"
                    candidate.contact_status = "email_invite_pending" if candidate.email else "email_missing"
                    candidate.email_invite_status = "pending" if candidate.email else "missing"
                    scoring_repo.delete_for_candidate_vacancy(candidate.id, vacancy_id)
                    scoring_repo.create(candidate_id=candidate.id, vacancy_id=vacancy_id, **score)
                    candidate.status = "scored"
                    task_db.commit()
                    logger.info("Resume processed successfully candidate_id=%s resume_id=%s", candidate.id, resume.id)
                    return {
                        "status": "processed",
                        "candidate_id": candidate.id,
                        "resume_id": resume.id,
                        "file_name": stored_file.original_name,
                    }
                except Exception as exc:
                    logger.exception("Resume processing failed file=%s", stored_file.original_name)
                    resume = task_db.get(type(resume), resume.id)
                    candidate = task_db.get(type(candidate), candidate.id)
                    resume.parse_status = "parse_failed"
                    resume.parse_error = str(exc)
                    resume.raw_text = raw_text
                    candidate.status = "parse_failed"
                    candidate.contact_status = "contact_failed"
                    task_db.commit()
                    if "empty" in str(exc).lower():
                        return {
                            "status": "empty",
                            "candidate_id": candidate.id,
                            "resume_id": resume.id,
                            "file_name": stored_file.original_name,
                            "error": str(exc),
                        }
                    return {
                        "status": "parse_failed",
                        "candidate_id": candidate.id,
                        "resume_id": resume.id,
                        "file_name": stored_file.original_name,
                        "error": str(exc),
                    }

    @staticmethod
    def _apply_candidate_profile(candidate: Candidate, profile: CandidateProfile) -> None:
        candidate.full_name = profile.full_name
        candidate.email = profile.email
        candidate.phone = profile.phone
        candidate.location = profile.location
        candidate.telegram_username = profile.telegram_username.lstrip("@") if profile.telegram_username else None
