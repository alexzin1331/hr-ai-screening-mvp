from __future__ import annotations

from sqlalchemy import select

from app.models.resume import Resume
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository):
    def create(self, **data) -> Resume:
        resume = Resume(**data)
        self.db.add(resume)
        self.db.flush()
        self.db.refresh(resume)
        return resume

    def get(self, resume_id: int) -> Resume | None:
        return self.db.get(Resume, resume_id)

    def list_by_candidate(self, candidate_id: int) -> list[Resume]:
        return list(self.db.scalars(select(Resume).where(Resume.candidate_id == candidate_id)))
