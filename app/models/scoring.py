from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Scoring(Base):
    __tablename__ = "scorings"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True, nullable=False)
    score_resume: Mapped[float | None] = mapped_column(Float)
    score_dialog: Mapped[float | None] = mapped_column(Float)
    total_score: Mapped[float | None] = mapped_column(Float, index=True)
    match_strengths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    match_gaps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate = relationship("Candidate", back_populates="scorings")
    vacancy = relationship("Vacancy", back_populates="scorings")
