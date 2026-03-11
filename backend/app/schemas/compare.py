from datetime import date

from pydantic import BaseModel

from app.schemas.event import EventRead
from app.schemas.series import SeriesRead


class CompareObservationRead(BaseModel):
    date: date
    value_a: float | None
    value_b: float | None


class CompareResponse(BaseModel):
    series_a: SeriesRead
    series_b: SeriesRead
    observations: list[CompareObservationRead]
    events: list[EventRead]
