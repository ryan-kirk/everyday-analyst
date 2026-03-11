from __future__ import annotations

import os
from datetime import date
from typing import Any

import requests
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.observation import Observation
from app.models.series import Series

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_SOURCE = "fred"
SERIES_CATEGORY_OVERRIDES = {
    "DGS2": "treasury_rates",
    "UNRATE": "labor",
}


def _get_fred_api_key() -> str:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set. Add it to your environment before ingestion.")
    return api_key


def _fred_get(endpoint: str, **params: Any) -> dict[str, Any]:
    query_params = {
        "api_key": _get_fred_api_key(),
        "file_type": "json",
        **params,
    }
    response = requests.get(f"{FRED_API_BASE_URL}{endpoint}", params=query_params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_series_metadata(series_id: str) -> dict[str, str | None]:
    payload = _fred_get("/series", series_id=series_id)
    series_items = payload.get("seriess", [])
    if not series_items:
        raise ValueError(f"FRED metadata not found for series_id={series_id}")

    item = series_items[0]
    return {
        "name": item.get("title", series_id),
        "source": FRED_SOURCE,
        "source_series_id": series_id,
        "units": item.get("units_short") or item.get("units"),
        "frequency": item.get("frequency_short") or item.get("frequency"),
        "category": SERIES_CATEGORY_OVERRIDES.get(series_id),
    }


def fetch_series_observations(series_id: str) -> list[Observation]:
    payload = _fred_get(
        "/series/observations",
        series_id=series_id,
        sort_order="asc",
    )
    raw_observations = payload.get("observations", [])

    normalized: list[Observation] = []
    for item in raw_observations:
        value_raw = item.get("value")
        observation_date_raw = item.get("date")
        if value_raw in (None, ".", "") or not observation_date_raw:
            continue

        try:
            normalized.append(
                Observation(
                    series_id=0,
                    observation_date=date.fromisoformat(observation_date_raw),
                    value=float(value_raw),
                )
            )
        except (TypeError, ValueError):
            continue

    return normalized


def store_observations(series_id: str, observations: list[Observation]) -> int:
    metadata = fetch_series_metadata(series_id)

    with SessionLocal() as db:
        series = db.scalar(
            select(Series).where(
                Series.source == FRED_SOURCE,
                Series.source_series_id == series_id,
            )
        )

        if series is None:
            series = Series(
                name=metadata["name"] or series_id,
                source=FRED_SOURCE,
                source_series_id=series_id,
                units=metadata["units"],
                frequency=metadata["frequency"],
                category=metadata["category"],
            )
            db.add(series)
            db.flush()
        else:
            series.name = metadata["name"] or series.name
            series.units = metadata["units"]
            series.frequency = metadata["frequency"]
            series.category = metadata["category"]

        existing_by_date = {
            row.observation_date: row
            for row in db.scalars(
                select(Observation).where(Observation.series_id == series.id)
            ).all()
        }

        changed_count = 0
        for obs in observations:
            existing = existing_by_date.get(obs.observation_date)
            if existing is None:
                db.add(
                    Observation(
                        series_id=series.id,
                        observation_date=obs.observation_date,
                        value=obs.value,
                    )
                )
                changed_count += 1
            elif existing.value != obs.value:
                existing.value = obs.value
                changed_count += 1

        db.commit()
        return changed_count

