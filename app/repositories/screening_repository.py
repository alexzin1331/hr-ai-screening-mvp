from __future__ import annotations

from sqlalchemy import select

from app.models.screening_session import ScreeningSession
from app.repositories.base import BaseRepository


class ScreeningRepository(BaseRepository):
    def create(self, **data) -> ScreeningSession:
        session = ScreeningSession(**data)
        self.db.add(session)
        self.db.flush()
        self.db.refresh(session)
        return session

    def list_by_vacancy(self, vacancy_id: int) -> list[ScreeningSession]:
        return list(self.db.scalars(select(ScreeningSession).where(ScreeningSession.vacancy_id == vacancy_id)))
