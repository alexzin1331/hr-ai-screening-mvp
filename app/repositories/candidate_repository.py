from __future__ import annotations

from sqlalchemy import select

from app.models.candidate import Candidate
from app.repositories.base import BaseRepository


class CandidateRepository(BaseRepository):
    def create(self, **data) -> Candidate:
        candidate = Candidate(**data)
        self.db.add(candidate)
        self.db.flush()
        self.db.refresh(candidate)
        return candidate

    def get(self, candidate_id: int) -> Candidate | None:
        return self.db.get(Candidate, candidate_id)

    def list(self) -> list[Candidate]:
        return list(self.db.scalars(select(Candidate).order_by(Candidate.created_at.desc())))

    def get_by_invite_token(self, invite_token: str) -> Candidate | None:
        return self.db.execute(select(Candidate).where(Candidate.invite_token == invite_token)).scalars().first()

    def get_by_telegram_chat_id(self, telegram_chat_id: str) -> Candidate | None:
        return self.db.execute(
            select(Candidate).where(Candidate.telegram_chat_id == telegram_chat_id)
        ).scalars().first()
