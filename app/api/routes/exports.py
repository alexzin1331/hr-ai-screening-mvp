from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.vacancy import Vacancy
from app.repositories.audit_repository import AuditRepository
from app.services.export_service import ExportService


router = APIRouter(tags=["exports"])


@router.get("/vacancies/{vacancy_id}/export")
def export_candidates(
    vacancy_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
) -> Response:
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise NotFoundError(f"Vacancy {vacancy_id} not found")
    service = ExportService(db)
    AuditRepository(db).log(
        action="export_results",
        entity_type="vacancy",
        entity_id=str(vacancy_id),
        payload={"format": format},
        message="Экспортированы результаты по вакансии",
    )
    db.commit()
    if format == "csv":
        data = service.to_csv_bytes(vacancy_id)
        media_type = "text/csv; charset=utf-8"
        filename = f"vacancy-{vacancy_id}-results.csv"
    else:
        data = service.to_json_bytes(vacancy_id)
        media_type = "application/json"
        filename = f"vacancy-{vacancy_id}-results.json"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
