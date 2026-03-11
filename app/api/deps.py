from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.screening import ScreeningService


def get_screening_service(db: Session = Depends(get_db)) -> ScreeningService:
    return ScreeningService(db)
