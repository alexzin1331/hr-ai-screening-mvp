from __future__ import annotations

from sqlalchemy import select

from app.models.vacancy import Vacancy
from app.repositories.base import BaseRepository


class VacancyRepository(BaseRepository):
    def create(self, **data) -> Vacancy:
        vacancy = Vacancy(**data)
        self.db.add(vacancy)
        self.db.flush()
        self.db.refresh(vacancy)
        return vacancy

    def list(self) -> list[Vacancy]:
        return list(self.db.scalars(select(Vacancy).order_by(Vacancy.created_at.desc())))

    def get(self, vacancy_id: int) -> Vacancy | None:
        return self.db.get(Vacancy, vacancy_id)
