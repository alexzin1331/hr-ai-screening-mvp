from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Candidate(TimestampMixin, Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    telegram_username: Mapped[str | None] = mapped_column(String(100), index=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), index=True)
    telegram_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contact_status: Mapped[str] = mapped_column(String(50), default="new", index=True, nullable=False)
    invite_token: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    invite_token_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_invite_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_invite_status: Mapped[str | None] = mapped_column(String(50), index=True)
    telegram_last_error: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str | None] = mapped_column(String(100), default="upload")
    status: Mapped[str] = mapped_column(String(50), default="new", index=True, nullable=False)
    consent_to_personal_data_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    scorings = relationship("Scoring", back_populates="candidate", cascade="all, delete-orphan")
    sessions = relationship("ScreeningSession", back_populates="candidate", cascade="all, delete-orphan")
