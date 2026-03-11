from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal


router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "db": "unknown",
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/health/ready")
def ready() -> dict:
    settings = get_settings()
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "db": "ok",
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/health")
def legacy_health() -> dict:
    return {"status": "ok"}
