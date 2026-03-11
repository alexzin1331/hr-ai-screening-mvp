from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CandidateProfile(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    telegram_username: str | None = None
    total_years_experience: float | None = None
    current_position: str | None = None
    seniority_level: str | None = None
    skills_technical: list[str] = Field(default_factory=list)
    skills_soft: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    previous_companies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    english_level: str | None = None
    key_strengths: list[str] = Field(default_factory=list)
    possible_weaknesses: list[str] = Field(default_factory=list)
    salary_expectation: str | None = None
    summary: str | None = None


class CandidateRead(ORMModel):
    id: int
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    telegram_username: str | None
    telegram_chat_id: str | None
    telegram_connected_at: datetime | None
    contact_status: str
    invite_token_created_at: datetime | None
    email_invite_sent_at: datetime | None
    email_invite_status: str | None
    telegram_last_error: str | None
    source: str | None
    status: str
    consent_to_personal_data_processing: bool
    created_at: datetime
    updated_at: datetime


class CandidateListItem(BaseModel):
    candidate_id: int
    vacancy_id: int | None
    full_name: str | None
    email: str | None
    telegram_username: str | None
    telegram_chat_id: str | None
    current_position: str | None
    total_years_experience: float | None
    seniority_level: str | None
    summary: str | None
    parse_status: str
    candidate_status: str
    contact_status: str
    email_invite_status: str | None
    scoring_status: str
    score_resume: float | None
    score_dialog: float | None
    total_score: float | None
    match_strengths: list[str]
    match_gaps: list[str]
    reason: str | None
    resume_id: int
    created_at: datetime
