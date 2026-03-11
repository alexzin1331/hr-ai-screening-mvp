from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    async def complete_json(self, prompt: str, json_schema: dict, *, temperature: float = 0.0) -> dict:
        raise NotImplementedError
