from __future__ import annotations

import hashlib
import re

from app.integrations.llm.base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    async def complete_json(self, prompt: str, json_schema: dict, *, temperature: float = 0.0) -> dict:
        lowered = prompt.lower()
        if "evaluate candidate fit" in lowered:
            score = 55 + int(hashlib.md5(prompt.encode()).hexdigest(), 16) % 40
            return {
                "score_resume": score,
                "match_strengths": ["Базовое совпадение по стеку", "Опыт подтвержден резюме"],
                "match_gaps": ["Требуется ручная верификация деталей"],
                "reason": "Mock scoring provider generated a deterministic result for local testing.",
            }

        email = _extract(r"[\w.+-]+@[\w.-]+\.\w+", prompt)
        phone = _extract(r"\+?\d[\d\s().-]{7,}\d", prompt)
        telegram = _extract(r"(?:https?://t\.me/|@)([A-Za-z0-9_]{5,})", prompt, group=1)
        name = _extract(r"(?:name|имя)[:\s]+([A-ZА-Я][^\n,]{3,60})", prompt, group=1) or "Unknown Candidate"
        summary = "Mock summary based on uploaded resume text."
        return {
            "full_name": name.strip(),
            "email": email,
            "phone": phone,
            "location": None,
            "telegram_username": telegram,
            "total_years_experience": 3,
            "current_position": "Software Engineer",
            "seniority_level": "Middle",
            "skills_technical": ["Python", "FastAPI"],
            "skills_soft": ["Communication"],
            "programming_languages": ["Python"],
            "frameworks": ["FastAPI"],
            "databases": ["PostgreSQL"],
            "cloud": [],
            "tools": ["Docker"],
            "education": [],
            "languages": ["Russian"],
            "previous_companies": [],
            "projects": [],
            "english_level": "B1",
            "key_strengths": ["Structured backend thinking"],
            "possible_weaknesses": [],
            "salary_expectation": None,
            "summary": summary,
        }


def _extract(pattern: str, text: str, group: int = 0) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(group)
