from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.core.exceptions import LLMExtractionError
from app.integrations.llm.base import BaseLLMClient


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete_json(self, prompt: str, json_schema: dict, *, temperature: float = 0.0) -> dict:
        if not self.settings.llm_api_key:
            raise LLMExtractionError("LLM API key is not configured")

        payload = {
            "model": self.settings.llm_model,
            "temperature": temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not add markdown fences or commentary.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMExtractionError("LLM returned invalid JSON", {"raw_response": content[:500]}) from exc
