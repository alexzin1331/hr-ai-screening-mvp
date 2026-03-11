from __future__ import annotations

from app.core.config import get_settings
from app.integrations.llm.base import BaseLLMClient
from app.integrations.llm.mock import MockLLMClient
from app.integrations.llm.openai_compatible import OpenAICompatibleLLMClient


def get_llm_client() -> BaseLLMClient:
    settings = get_settings()
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleLLMClient(settings)
    return MockLLMClient()
