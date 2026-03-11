from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.observation import Observation
from app.models.series import Series


def list_series(db: Session) -> list[Series]:
    stmt: Select[tuple[Series]] = select(Series).order_by(Series.name.asc())
    return list(db.scalars(stmt).all())


def get_observations(
    db: Session,
    series_id: int,
    start: date | None = None,
    end: date | None = None,
) -> list[Observation]:
    stmt: Select[tuple[Observation]] = (
        select(Observation)
        .where(Observation.series_id == series_id)
        .order_by(Observation.observation_date.asc())
    )
    if start is not None:
        stmt = stmt.where(Observation.observation_date >= start)
    if end is not None:
        stmt = stmt.where(Observation.observation_date <= end)
    return list(db.scalars(stmt).all())

