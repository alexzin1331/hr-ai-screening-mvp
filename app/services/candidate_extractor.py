from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import LLMExtractionError
from app.integrations.llm.base import BaseLLMClient
from app.integrations.llm.factory import get_llm_client
from app.schemas.candidate import CandidateProfile


logger = logging.getLogger(__name__)
TG_USERNAME_PATTERN = re.compile(r"(?:https?://t\.me/|@)([A-Za-z0-9_]{5,})")


class CandidateExtractorService:
    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.settings = get_settings()
        self.llm_client = llm_client or get_llm_client()
        self.semaphore = asyncio.Semaphore(self.settings.llm_concurrency_limit)

    async def extract(self, raw_text: str) -> CandidateProfile:
        prompt = self._build_prompt(raw_text)
        schema = self._json_schema()
        retries = self.settings.llm_max_retries + 1

        async with self.semaphore:
            for attempt in range(1, retries + 1):
                try:
                    logger.info("Calling LLM for candidate extraction attempt=%s", attempt)
                    payload = await self.llm_client.complete_json(prompt, schema, temperature=0.0)
                    normalized = self._normalize_payload(payload, raw_text)
                    return CandidateProfile.model_validate(normalized)
                except Exception as exc:
                    logger.warning("Candidate extraction attempt failed attempt=%s error=%s", attempt, str(exc))
                    if attempt == retries:
                        raise LLMExtractionError("Failed to extract candidate profile from resume") from exc
                    await asyncio.sleep(min(attempt, 3))

        raise LLMExtractionError("LLM extraction failed after retries")

    def _normalize_payload(self, payload: dict[str, Any], raw_text: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise LLMExtractionError("LLM returned non-object JSON")

        normalized: dict[str, Any] = {}
        for key in self._json_schema()["properties"]:
            value = payload.get(key)
            if isinstance(value, str):
                value = value.strip() or None
            if isinstance(value, list):
                value = [str(item).strip() for item in value if str(item).strip()]
            normalized[key] = value

        if not normalized.get("telegram_username"):
            match = TG_USERNAME_PATTERN.search(raw_text or "")
            if match:
                normalized["telegram_username"] = match.group(1)

        return normalized

    def _build_prompt(self, raw_text: str) -> str:
        schema = json.dumps(self._json_schema(), ensure_ascii=False)
        return (
            "Ты HR parser. Извлеки структуру кандидата из текста резюме. "
            "Верни только JSON строго по JSON Schema.\n"
            f"JSON Schema: {schema}\n"
            f"Resume text:\n{raw_text}"
        )

    @staticmethod
    def _json_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "full_name": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "telegram_username": {"type": ["string", "null"]},
                "total_years_experience": {"type": ["number", "null"]},
                "current_position": {"type": ["string", "null"]},
                "seniority_level": {"type": ["string", "null"]},
                "skills_technical": {"type": "array", "items": {"type": "string"}},
                "skills_soft": {"type": "array", "items": {"type": "string"}},
                "programming_languages": {"type": "array", "items": {"type": "string"}},
                "frameworks": {"type": "array", "items": {"type": "string"}},
                "databases": {"type": "array", "items": {"type": "string"}},
                "cloud": {"type": "array", "items": {"type": "string"}},
                "tools": {"type": "array", "items": {"type": "string"}},
                "education": {"type": "array", "items": {"type": "string"}},
                "languages": {"type": "array", "items": {"type": "string"}},
                "previous_companies": {"type": "array", "items": {"type": "string"}},
                "projects": {"type": "array", "items": {"type": "string"}},
                "english_level": {"type": ["string", "null"]},
                "key_strengths": {"type": "array", "items": {"type": "string"}},
                "possible_weaknesses": {"type": "array", "items": {"type": "string"}},
                "salary_expectation": {"type": ["string", "null"]},
                "summary": {"type": ["string", "null"]},
            },
            "required": [],
            "additionalProperties": False,
        }
