from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import TelegramDeliveryError


logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _api_url(self, method: str) -> str:
        return f"{self.settings.telegram_api_base}/bot{self.settings.telegram_bot_token}/{method}"

    async def send_message(self, chat_id: str | int, message: str) -> dict:
        if not self.settings.telegram_bot_token:
            logger.info("Telegram token is not configured, using dry-run delivery chat_id=%s", chat_id)
            return {
                "ok": True,
                "dry_run": True,
                "chat_id": str(chat_id),
            }

        endpoint = self._api_url("sendMessage")
        payload = {"chat_id": str(chat_id), "text": message}
        logger.info("Sending telegram message chat_id=%s", chat_id)
        try:
            async with httpx.AsyncClient(timeout=self.settings.telegram_timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise TelegramDeliveryError("Failed to send Telegram message", {"chat_id": str(chat_id)}) from exc

    async def get_updates(self, *, offset: int | None = None, timeout: int | None = None) -> list[dict[str, Any]]:
        if not self.settings.telegram_bot_token:
            logger.info("Telegram token is not configured, polling disabled in dry-run mode")
            return []

        payload: dict[str, Any] = {
            "timeout": timeout or self.settings.telegram_polling_timeout_seconds,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset

        endpoint = self._api_url("getUpdates")
        timeout = httpx.Timeout(
            connect=min(self.settings.telegram_timeout_seconds, 10),
            read=self.settings.telegram_polling_timeout_seconds + 10,
            write=self.settings.telegram_timeout_seconds,
            pool=self.settings.telegram_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise TelegramDeliveryError("Failed to fetch Telegram updates", {"response": data})
        return data.get("result", [])

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> dict[str, Any]:
        if not self.settings.telegram_bot_token:
            return {"ok": True, "dry_run": True}
        endpoint = self._api_url("deleteWebhook")
        payload = {"drop_pending_updates": drop_pending_updates}
        async with httpx.AsyncClient(timeout=self.settings.telegram_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
        return response.json()
