from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class ScreeningSession(TimestampMixin, Base):
    __tablename__ = "screening_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    last_message_at: Mapped[str | None] = mapped_column(String(100))
    messages_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)

    candidate = relationship("Candidate", back_populates="sessions")
    vacancy = relationship("Vacancy", back_populates="sessions")
