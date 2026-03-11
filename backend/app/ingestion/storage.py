from __future__ import annotations

import logging
from typing import TypedDict

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.event import Event
from app.models.observation import Observation
from app.models.series import Series

logger = logging.getLogger(__name__)


class SeriesMetadata(TypedDict):
    name: str
    source: str
    source_series_id: str
    units: str | None
    frequency: str | None
    category: str | None


def store_series_observations(
    metadata: SeriesMetadata,
    observations: list[Observation],
) -> dict[str, int]:
    """Upsert series metadata and observations into normalized tables."""
    with SessionLocal() as db:
        series = db.scalar(
            select(Series).where(
                Series.source == metadata["source"],
                Series.source_series_id == metadata["source_series_id"],
            )
        )

        if series is None:
            series = Series(
                name=metadata["name"],
                source=metadata["source"],
                source_series_id=metadata["source_series_id"],
                units=metadata["units"],
                frequency=metadata["frequency"],
                category=metadata["category"],
            )
            db.add(series)
            db.flush()
        else:
            series.name = metadata["name"]
            series.units = metadata["units"]
            series.frequency = metadata["frequency"]
            series.category = metadata["category"]

        incoming_by_date = {obs.observation_date: obs.value for obs in observations}
        existing_by_date = {
            row.observation_date: row
            for row in db.scalars(
                select(Observation).where(Observation.series_id == series.id)
            ).all()
        }

        inserted = 0
        updated = 0

        for obs_date, obs_value in sorted(incoming_by_date.items()):
            existing = existing_by_date.get(obs_date)
            if existing is None:
                db.add(Observation(series_id=series.id, observation_date=obs_date, value=obs_value))
                inserted += 1
                continue
            if existing.value != obs_value:
                existing.value = obs_value
                updated += 1

        db.commit()

    total_changed = inserted + updated
    logger.info(
        "Stored series source=%s source_series_id=%s inserted=%s updated=%s changed=%s",
        metadata["source"],
        metadata["source_series_id"],
        inserted,
        updated,
        total_changed,
    )
    return {
        "inserted": inserted,
        "updated": updated,
        "changed": total_changed,
        "fetched": len(observations),
    }


def store_events(events: list[Event]) -> dict[str, int]:
    """Upsert events by (event_date, title, category, source)."""
    with SessionLocal() as db:
        existing = db.scalars(select(Event)).all()
        existing_by_key = {
            (row.event_date, row.title, row.category, row.source): row for row in existing
        }

        inserted = 0
        updated = 0

        for event in events:
            key = (event.event_date, event.title, event.category, event.source)
            row = existing_by_key.get(key)
            if row is None:
                db.add(
                    Event(
                        event_date=event.event_date,
                        title=event.title,
                        summary=event.summary,
                        category=event.category,
                        source=event.source,
                        importance_score=event.importance_score,
                    )
                )
                inserted += 1
                continue

            has_changed = False
            if row.summary != event.summary:
                row.summary = event.summary
                has_changed = True
            if row.importance_score != event.importance_score:
                row.importance_score = event.importance_score
                has_changed = True
            if has_changed:
                updated += 1

        db.commit()

    changed = inserted + updated
    logger.info(
        "Stored events fetched=%s inserted=%s updated=%s changed=%s",
        len(events),
        inserted,
        updated,
        changed,
    )
    return {"fetched": len(events), "inserted": inserted, "updated": updated, "changed": changed}
