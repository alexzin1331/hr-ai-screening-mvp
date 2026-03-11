from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class VacancyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10)
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    seniority: str | None = Field(default=None, max_length=50)
    status: str = Field(default="draft", max_length=50)
    created_by: int | None = None


class LegacyVacancyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    skills: str = Field(min_length=2)
    description: str = Field(min_length=10)
    seniority: str | None = None


class VacancyRead(ORMModel):
    id: int
    title: str
    description: str
    hard_skills: list[str]
    soft_skills: list[str]
    seniority: str | None
    status: str
    created_by: int | None
    created_at: datetime
    updated_at: datetime
