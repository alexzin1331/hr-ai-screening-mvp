from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import LLMExtractionError
from app.integrations.llm.base import BaseLLMClient
from app.integrations.llm.factory import get_llm_client
from app.models.vacancy import Vacancy
from app.schemas.candidate import CandidateProfile


logger = logging.getLogger(__name__)


class ScoringService:
    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.settings = get_settings()
        self.llm_client = llm_client or get_llm_client()
        self.semaphore = asyncio.Semaphore(self.settings.llm_concurrency_limit)

    async def score(self, vacancy: Vacancy, candidate: CandidateProfile) -> dict[str, Any]:
        prompt = self._build_prompt(vacancy, candidate)
        schema = {
            "type": "object",
            "properties": {
                "score_resume": {"type": ["number", "null"]},
                "match_strengths": {"type": "array", "items": {"type": "string"}},
                "match_gaps": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": ["string", "null"]},
            },
            "required": ["score_resume", "match_strengths", "match_gaps", "reason"],
            "additionalProperties": False,
        }
        retries = self.settings.llm_max_retries + 1

        async with self.semaphore:
            for attempt in range(1, retries + 1):
                try:
                    logger.info("Calling LLM for scoring attempt=%s vacancy_id=%s", attempt, vacancy.id)
                    payload = await self.llm_client.complete_json(prompt, schema, temperature=0.0)
                    score_resume = float(payload.get("score_resume") or 0)
                    return {
                        "score_resume": max(0.0, min(100.0, score_resume)),
                        "score_dialog": None,
                        "total_score": max(0.0, min(100.0, score_resume)),
                        "match_strengths": payload.get("match_strengths") or [],
                        "match_gaps": payload.get("match_gaps") or [],
                        "reason": payload.get("reason"),
                    }
                except Exception as exc:
                    logger.warning("Scoring attempt failed attempt=%s error=%s", attempt, str(exc))
                    if attempt == retries:
                        raise LLMExtractionError("Failed to score candidate against vacancy") from exc
                    await asyncio.sleep(min(attempt, 3))

        raise LLMExtractionError("Scoring failed after retries")

    @staticmethod
    def _build_prompt(vacancy: Vacancy, candidate: CandidateProfile) -> str:
        return f"""
Evaluate candidate fit for vacancy.

Vacancy:
- title: {vacancy.title}
- description: {vacancy.description}
- hard_skills: {vacancy.hard_skills}
- soft_skills: {vacancy.soft_skills}
- seniority: {vacancy.seniority}

Candidate:
{candidate.model_dump_json(indent=2)}

Return strict JSON with fields:
score_resume, match_strengths, match_gaps, reason
"""
