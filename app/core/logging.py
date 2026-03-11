from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import (
    candidate_id_ctx,
    request_id_ctx,
    resume_id_ctx,
    set_request_id,
    vacancy_id_ctx,
)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.vacancy_id = vacancy_id_ctx.get()
        record.candidate_id = candidate_id_ctx.get()
        record.resume_id = resume_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "vacancy_id": getattr(record, "vacancy_id", "-"),
            "candidate_id": getattr(record, "candidate_id", "-"),
            "resume_id": getattr(record, "resume_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(debug: bool = False) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if debug:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | req=%(request_id)s | vac=%(vacancy_id)s | "
            "cand=%(candidate_id)s | resume=%(resume_id)s | %(message)s"
        )
    else:
        formatter = JsonFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        set_request_id(request_id)
        start = time.perf_counter()
        self.logger.info("HTTP request started %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            self.logger.exception("HTTP request failed %s %s", request.method, request.url.path)
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        self.logger.info(
            "HTTP request finished %s %s status=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
