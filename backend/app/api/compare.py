from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.compare import CompareResponse
from app.services.compare_service import (
    get_aligned_observations,
    get_events_in_range,
    get_series_by_id,
)

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareResponse)
def compare_series(
    series_a: int,
    series_b: int,
    start: date | None = None,
    end: date | None = None,
    event_category: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CompareResponse:
    series_a_record = get_series_by_id(db, series_a)
    if series_a_record is None:
        raise HTTPException(status_code=404, detail=f"Series not found for series_a={series_a}")

    series_b_record = get_series_by_id(db, series_b)
    if series_b_record is None:
        raise HTTPException(status_code=404, detail=f"Series not found for series_b={series_b}")

    aligned = get_aligned_observations(
        db=db,
        series_a_id=series_a,
        series_b_id=series_b,
        start=start,
        end=end,
    )
    categories = _normalize_event_categories(event_category)
    events = get_events_in_range(db=db, start=start, end=end, categories=categories)

    return CompareResponse(
        series_a=series_a_record,
        series_b=series_b_record,
        observations=aligned,
        events=events,
    )


def _normalize_event_categories(raw_values: list[str] | None) -> list[str] | None:
    if not raw_values:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for value in raw.split(","):
            category = value.strip().lower()
            if category and category not in seen:
                normalized.append(category)
                seen.add(category)
    return normalized or None
