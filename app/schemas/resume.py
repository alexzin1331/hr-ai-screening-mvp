from __future__ import annotations

from pydantic import BaseModel, Field


class UploadSummary(BaseModel):
    batch_id: str
    vacancy_id: int
    processed: int
    created_candidates: int
    parse_failed: int
    skipped_unsupported: int
    skipped_empty: int
    skipped_errors: int
    files: list[dict]


class UploadOptions(BaseModel):
    consent_to_personal_data_processing: bool = Field(default=True)
