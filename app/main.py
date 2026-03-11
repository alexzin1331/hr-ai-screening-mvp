from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import base as _db_models  # noqa: F401
from app.api.routes.candidates import legacy_router as legacy_candidates_router
from app.api.routes.candidates import router as candidates_router
from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.screening import legacy_router as legacy_screening_router
from app.api.routes.screening import router as screening_router
from app.api.routes.uploads import legacy_router as legacy_uploads_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.vacancies import legacy_router as legacy_vacancies_router
from app.api.routes.vacancies import router as vacancies_router
from app.core.config import BASE_DIR, get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging
from app.services.telegram_polling import TelegramPollingWorker


settings = get_settings()
configure_logging(debug=settings.debug)
logger = logging.getLogger(__name__)
polling_worker = TelegramPollingWorker()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await polling_worker.start()
    try:
        yield
    finally:
        await polling_worker.stop()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware, logger=logger)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(vacancies_router, prefix=settings.api_prefix)
app.include_router(candidates_router, prefix=settings.api_prefix)
app.include_router(uploads_router, prefix=settings.api_prefix)
app.include_router(screening_router, prefix=settings.api_prefix)
app.include_router(exports_router, prefix=settings.api_prefix)
app.include_router(legacy_vacancies_router)
app.include_router(legacy_candidates_router)
app.include_router(legacy_uploads_router)
app.include_router(legacy_screening_router)

dashboard_dir = BASE_DIR / "dashboard"
app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir)), name="dashboard")


@app.get("/", include_in_schema=False)
def dashboard_index() -> FileResponse:
    return FileResponse(dashboard_dir / "index.html")


@app.get("/app.js", include_in_schema=False)
def dashboard_app_js() -> FileResponse:
    return FileResponse(dashboard_dir / "app.js", media_type="application/javascript")


@app.get("/styles.css", include_in_schema=False)
def dashboard_styles() -> FileResponse:
    return FileResponse(dashboard_dir / "styles.css", media_type="text/css")
