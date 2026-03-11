from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.observation import Observation
from app.models.series import Series
from app.schemas.compare import CompareObservationRead


def get_series_by_id(db: Session, series_id: int) -> Series | None:
    stmt: Select[tuple[Series]] = select(Series).where(Series.id == series_id)
    return db.scalar(stmt)


def get_aligned_observations(
    db: Session,
    series_a_id: int,
    series_b_id: int,
    start: date | None = None,
    end: date | None = None,
) -> list[CompareObservationRead]:
    stmt_a = select(Observation.observation_date, Observation.value).where(
        Observation.series_id == series_a_id
    )
    stmt_b = select(Observation.observation_date, Observation.value).where(
        Observation.series_id == series_b_id
    )
    all_dates_stmt = select(Observation.observation_date).where(
        Observation.series_id.in_([series_a_id, series_b_id])
    )

    if start is not None:
        stmt_a = stmt_a.where(Observation.observation_date >= start)
        stmt_b = stmt_b.where(Observation.observation_date >= start)
        all_dates_stmt = all_dates_stmt.where(Observation.observation_date >= start)
    if end is not None:
        stmt_a = stmt_a.where(Observation.observation_date <= end)
        stmt_b = stmt_b.where(Observation.observation_date <= end)
        all_dates_stmt = all_dates_stmt.where(Observation.observation_date <= end)

    rows_a = db.execute(stmt_a).all()
    rows_b = db.execute(stmt_b).all()
    all_dates = [
        row.observation_date
        for row in db.execute(
            all_dates_stmt.distinct().order_by(Observation.observation_date.asc())
        ).all()
    ]

    values_a_by_date = {row.observation_date: row.value for row in rows_a}
    values_b_by_date = {row.observation_date: row.value for row in rows_b}

    return [
        CompareObservationRead(
            date=obs_date,
            value_a=values_a_by_date.get(obs_date),
            value_b=values_b_by_date.get(obs_date),
        )
        for obs_date in all_dates
    ]
