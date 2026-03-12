from datetime import date

from pydantic import BaseModel

from app.schemas.event import EventRead
from app.schemas.series import SeriesRead


class InsightInflectionPoint(BaseModel):
    date: date
    series: str
    direction: str
    delta: float
    nearby_events: list[EventRead]


class InsightMajorMovement(BaseModel):
    series: str
    start_date: date
    end_date: date
    change: float
    percent_change: float | None
    direction: str
    nearby_events: list[EventRead]


class InsightsResponse(BaseModel):
    series_a: SeriesRead
    series_b: SeriesRead
    start: date | None = None
    end: date | None = None
    aligned_points: int
    series_a_points: int
    series_b_points: int
    overlap_points: int
    overlap_method: str
    correlation: float | None
    inflection_points: list[InsightInflectionPoint]
    major_movements: list[InsightMajorMovement]
    narrative_summary: str
