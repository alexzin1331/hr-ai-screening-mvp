from __future__ import annotations

import csv
import io
import json
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.scoring import Scoring
from app.schemas.candidate import CandidateListItem


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def fetch_rows(self, vacancy_id: int) -> list[CandidateListItem]:
        stmt = (
            select(Candidate, Resume, Scoring)
            .join(Resume, Resume.candidate_id == Candidate.id)
            .join(Scoring, (Scoring.candidate_id == Candidate.id) & (Scoring.vacancy_id == vacancy_id))
            .order_by(Scoring.total_score.desc().nullslast(), Candidate.created_at.desc())
        )
        rows = []
        for candidate, resume, scoring in self.db.execute(stmt).all():
            parsed = resume.parsed_json or {}
            rows.append(
                CandidateListItem(
                    candidate_id=candidate.id,
                    vacancy_id=vacancy_id,
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
                    scoring_status="scored" if scoring.total_score is not None else "pending",
                    score_resume=scoring.score_resume,
                    score_dialog=scoring.score_dialog,
                    total_score=scoring.total_score,
                    match_strengths=scoring.match_strengths,
                    match_gaps=scoring.match_gaps,
                    reason=scoring.reason,
                    resume_id=resume.id,
                    created_at=candidate.created_at.astimezone(timezone.utc),
                )
            )
        return rows

    def to_json_bytes(self, vacancy_id: int) -> bytes:
        rows = [row.model_dump(mode="json") for row in self.fetch_rows(vacancy_id)]
        return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")

    def to_csv_bytes(self, vacancy_id: int) -> bytes:
        rows = self.fetch_rows(vacancy_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "candidate_id",
                "full_name",
                "email",
                "telegram_username",
                "telegram_chat_id",
                "current_position",
                "total_years_experience",
                "seniority_level",
                "parse_status",
                "candidate_status",
                "contact_status",
                "email_invite_status",
                "score_resume",
                "total_score",
                "summary",
                "match_strengths",
                "match_gaps",
                "reason",
            ],
        )
        writer.writeheader()
        for row in rows:
            payload = row.model_dump()
            payload["match_strengths"] = "; ".join(row.match_strengths)
            payload["match_gaps"] = "; ".join(row.match_gaps)
            writer.writerow({k: payload.get(k) for k in writer.fieldnames})
        return output.getvalue().encode("utf-8")
