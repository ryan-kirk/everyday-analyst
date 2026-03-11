from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.insights import InsightsResponse
from app.services.compare_service import get_series_by_id
from app.services.insight_service import generate_insights

router = APIRouter(tags=["insights"])


@router.get("/insights", response_model=InsightsResponse)
def get_insights(
    series_a: int,
    series_b: int,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> InsightsResponse:
    series_a_record = get_series_by_id(db, series_a)
    if series_a_record is None:
        raise HTTPException(status_code=404, detail=f"Series not found for series_a={series_a}")

    series_b_record = get_series_by_id(db, series_b)
    if series_b_record is None:
        raise HTTPException(status_code=404, detail=f"Series not found for series_b={series_b}")

    return generate_insights(
        db=db,
        series_a=series_a_record,
        series_b=series_b_record,
        start=start,
        end=end,
    )
