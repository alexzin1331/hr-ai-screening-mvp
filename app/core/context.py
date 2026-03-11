from __future__ import annotations

from contextvars import ContextVar


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
vacancy_id_ctx: ContextVar[str] = ContextVar("vacancy_id", default="-")
candidate_id_ctx: ContextVar[str] = ContextVar("candidate_id", default="-")
resume_id_ctx: ContextVar[str] = ContextVar("resume_id", default="-")


def set_request_id(value: str) -> None:
    request_id_ctx.set(value)


def set_vacancy_id(value: str | int) -> None:
    vacancy_id_ctx.set(str(value))


def set_candidate_id(value: str | int) -> None:
    candidate_id_ctx.set(str(value))


def set_resume_id(value: str | int) -> None:
    resume_id_ctx.set(str(value))
