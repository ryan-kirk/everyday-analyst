from datetime import date

from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    event_date: date
    title: str
    summary: str | None = None
    category: str | None = None
    source: str | None = None
    importance_score: float | None = None


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
