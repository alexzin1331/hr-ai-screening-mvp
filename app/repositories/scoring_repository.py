from __future__ import annotations

from sqlalchemy import delete, select

from app.models.scoring import Scoring
from app.repositories.base import BaseRepository


class ScoringRepository(BaseRepository):
    def create(self, **data) -> Scoring:
        scoring = Scoring(**data)
        self.db.add(scoring)
        self.db.flush()
        self.db.refresh(scoring)
        return scoring

    def delete_for_candidate_vacancy(self, candidate_id: int, vacancy_id: int) -> None:
        self.db.execute(
            delete(Scoring).where(Scoring.candidate_id == candidate_id, Scoring.vacancy_id == vacancy_id)
        )

    def list_by_vacancy(self, vacancy_id: int) -> list[Scoring]:
        return list(
            self.db.scalars(select(Scoring).where(Scoring.vacancy_id == vacancy_id).order_by(Scoring.total_score.desc()))
        )
