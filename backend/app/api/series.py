from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.series import ObservationRead, SeriesRead
from app.services.series_service import get_observations, list_series

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=list[SeriesRead])
def get_series(db: Session = Depends(get_db)) -> list[SeriesRead]:
    return list_series(db)


@router.get("/{series_id}/observations", response_model=list[ObservationRead])
def get_series_observations(
    series_id: int,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> list[ObservationRead]:
    return get_observations(db=db, series_id=series_id, start=start, end=end)
