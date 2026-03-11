from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.scoring import Scoring
from app.models.vacancy import Vacancy
from app.schemas.candidate import CandidateListItem, CandidateRead


router = APIRouter(tags=["candidates"])
legacy_router = APIRouter(tags=["legacy"])


def _build_candidate_items(rows, vacancy_id: int | None = None) -> list[CandidateListItem]:
    items: list[CandidateListItem] = []
    for candidate, resume, scoring in rows:
        parsed = resume.parsed_json or {}
        items.append(
            CandidateListItem(
                candidate_id=candidate.id,
                vacancy_id=vacancy_id or scoring.vacancy_id if scoring else None,
                full_name=candidate.full_name,
                email=candidate.email,
                telegram_username=candidate.telegram_username,
                telegram_chat_id=candidate.telegram_chat_id,
                current_position=parsed.get("current_position"),
                total_years_experience=parsed.get("total_years_experience"),
                seniority_level=parsed.get("seniority_level"),
                summary=parsed.get("summary"),
                parse_status=resume.parse_status,
                candidate_status=candidate.status,
                contact_status=candidate.contact_status,
                email_invite_status=candidate.email_invite_status,
                scoring_status="scored" if scoring and scoring.total_score is not None else "pending",
                score_resume=scoring.score_resume if scoring else None,
                score_dialog=scoring.score_dialog if scoring else None,
                total_score=scoring.total_score if scoring else None,
                match_strengths=scoring.match_strengths if scoring else [],
                match_gaps=scoring.match_gaps if scoring else [],
                reason=scoring.reason if scoring else None,
                resume_id=resume.id,
                created_at=candidate.created_at,
            )
        )
    return items


@router.get("/vacancies/{vacancy_id}/candidates", response_model=list[CandidateListItem])
def list_candidates_by_vacancy(vacancy_id: int, db: Session = Depends(get_db)) -> list[CandidateListItem]:
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    stmt = (
        select(Candidate, Resume, Scoring)
        .join(Resume, Resume.candidate_id == Candidate.id)
        .join(Scoring, (Scoring.candidate_id == Candidate.id) & (Scoring.vacancy_id == vacancy_id), isouter=True)
        .order_by(Scoring.total_score.desc().nullslast(), Candidate.created_at.desc())
    )
    return _build_candidate_items(db.execute(stmt).all(), vacancy_id)


@router.get("/candidates", response_model=list[CandidateListItem])
def list_candidates_legacy(vacancy_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[CandidateListItem]:
    if vacancy_id is None:
        vacancy = db.execute(select(Vacancy).order_by(Vacancy.created_at.desc())).scalars().first()
        if not vacancy:
            return []
        vacancy_id = vacancy.id
    stmt = (
        select(Candidate, Resume, Scoring)
        .join(Resume, Resume.candidate_id == Candidate.id)
        .join(Scoring, (Scoring.candidate_id == Candidate.id) & (Scoring.vacancy_id == vacancy_id), isouter=True)
        .order_by(Scoring.total_score.desc().nullslast(), Candidate.created_at.desc())
    )
    return _build_candidate_items(db.execute(stmt).all(), vacancy_id)


@legacy_router.get("/candidates", response_model=list[CandidateListItem])
def list_candidates_root(vacancy_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[CandidateListItem]:
    return list_candidates_legacy(vacancy_id=vacancy_id, db=db)


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found")
    return CandidateRead.model_validate(candidate)
