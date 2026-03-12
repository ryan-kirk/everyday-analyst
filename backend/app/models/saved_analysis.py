from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SavedAnalysis(Base):
    __tablename__ = "saved_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    series_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False, index=True)
    series_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    event_category_filter: Mapped[str | None] = mapped_column(String(200), nullable=True)

    is_bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    share_include_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    user = relationship("User", back_populates="saved_analyses")
    series_a = relationship("Series", foreign_keys=[series_a_id])
    series_b = relationship("Series", foreign_keys=[series_b_id])
    notes = relationship(
        "UserNote",
        back_populates="saved_analysis",
        cascade="all, delete-orphan",
    )
