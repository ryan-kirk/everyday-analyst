from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.event import Event


def list_events(
    db: Session,
    start: date | None = None,
    end: date | None = None,
    category: str | None = None,
) -> list[Event]:
    stmt: Select[tuple[Event]] = select(Event).order_by(Event.event_date.asc())
    if start is not None:
        stmt = stmt.where(Event.event_date >= start)
    if end is not None:
        stmt = stmt.where(Event.event_date <= end)
    if category is not None:
        stmt = stmt.where(Event.category == category)
    return list(db.scalars(stmt).all())


def list_event_categories(db: Session) -> list[str]:
    stmt: Select[tuple[str | None]] = (
        select(Event.category)
        .where(Event.category.is_not(None))
        .distinct()
        .order_by(Event.category.asc())
    )
    return [value for value in db.scalars(stmt).all() if value]
