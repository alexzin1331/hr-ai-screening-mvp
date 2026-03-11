from __future__ import annotations

from app.core.context import request_id_ctx
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        payload: dict | None = None,
        user_id: int | None = None,
        message: str | None = None,
    ) -> AuditLog:
        item = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            user_id=user_id,
            request_id=request_id_ctx.get(),
            message=message,
        )
        self.db.add(item)
        self.db.flush()
        return item
