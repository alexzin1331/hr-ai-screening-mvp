from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmailProvider(ABC):
    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str) -> dict:
        raise NotImplementedError
