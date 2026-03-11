from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.context import set_vacancy_id
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.repositories.audit_repository import AuditRepository
from app.repositories.vacancy_repository import VacancyRepository
from app.schemas.vacancy import LegacyVacancyCreate, VacancyCreate, VacancyRead


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vacancies", tags=["vacancies"])
legacy_router = APIRouter(tags=["legacy"])


@router.post("", response_model=VacancyRead, status_code=status.HTTP_201_CREATED)
def create_vacancy(payload: VacancyCreate, db: Session = Depends(get_db)) -> VacancyRead:
    repo = VacancyRepository(db)
    vacancy = repo.create(**payload.model_dump())
    set_vacancy_id(vacancy.id)
    AuditRepository(db).log(
        action="create_vacancy",
        entity_type="vacancy",
        entity_id=str(vacancy.id),
        payload=payload.model_dump(mode="json"),
        user_id=payload.created_by,
        message="Создана вакансия",
    )
    db.commit()
    logger.info("Vacancy created vacancy_id=%s", vacancy.id)
    return VacancyRead.model_validate(vacancy)


@router.get("", response_model=list[VacancyRead])
def list_vacancies(db: Session = Depends(get_db)) -> list[VacancyRead]:
    vacancies = VacancyRepository(db).list()
    return [VacancyRead.model_validate(vacancy) for vacancy in vacancies]


@router.get("/{vacancy_id}", response_model=VacancyRead)
def get_vacancy(vacancy_id: int, db: Session = Depends(get_db)) -> VacancyRead:
    vacancy = VacancyRepository(db).get(vacancy_id)
    if not vacancy:
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    return VacancyRead.model_validate(vacancy)


@legacy_router.post("/create_vacancy", response_model=VacancyRead, status_code=status.HTTP_201_CREATED)
def create_vacancy_legacy(payload: LegacyVacancyCreate, db: Session = Depends(get_db)) -> VacancyRead:
    hard_skills = [item.strip() for item in payload.skills.split(",") if item.strip()]
    vacancy = VacancyRepository(db).create(
        title=payload.title,
        description=payload.description,
        hard_skills=hard_skills,
        soft_skills=[],
        seniority=payload.seniority,
        status="active",
        created_by=None,
    )
    set_vacancy_id(vacancy.id)
    AuditRepository(db).log(
        action="create_vacancy",
        entity_type="vacancy",
        entity_id=str(vacancy.id),
        payload=payload.model_dump(mode="json"),
        message="Создана вакансия через legacy endpoint",
    )
    db.commit()
    return VacancyRead.model_validate(vacancy)
