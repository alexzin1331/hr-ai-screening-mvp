from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.screening import ScreeningService
from app.services.telegram_service import TelegramService


logger = logging.getLogger(__name__)


class TelegramPollingWorker:
    def __init__(self, telegram_service: TelegramService | None = None) -> None:
        self.settings = get_settings()
        self.telegram_service = telegram_service or TelegramService()
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._offset: int | None = None

    async def start(self) -> None:
        if not self.settings.telegram_polling_enabled:
            logger.info("Telegram polling is disabled")
            return
        if not self.settings.telegram_bot_token:
            logger.warning("Telegram polling enabled but TELEGRAM_BOT_TOKEN is not configured")
            return
        if self._task and not self._task.done():
            return

        logger.info("Starting Telegram polling worker")
        await self.telegram_service.delete_webhook(drop_pending_updates=False)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="telegram-polling-worker")

    async def stop(self) -> None:
        if not self._task:
            return
        logger.info("Stopping Telegram polling worker")
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                updates = await self.telegram_service.get_updates(offset=self._offset)
                for update in updates:
                    await self._handle_update(update)
                    self._offset = int(update["update_id"]) + 1
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram polling iteration failed")
                await asyncio.sleep(self.settings.telegram_polling_retry_delay_seconds)

    async def _handle_update(self, update: dict) -> None:
        update_id = update.get("update_id")
        logger.info("Processing polled telegram update update_id=%s", update_id)
        with SessionLocal() as db:
            service = ScreeningService(db, telegram_service=self.telegram_service)
            await service.process_telegram_update(update)
