from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class UserNote(Base):
    __tablename__ = "user_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    saved_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("saved_analyses.id"),
        nullable=False,
        index=True,
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    user = relationship("User", back_populates="notes")
    saved_analysis = relationship("SavedAnalysis", back_populates="notes")
