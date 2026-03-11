from datetime import date

from pydantic import BaseModel, ConfigDict


class SeriesBase(BaseModel):
    name: str
    source: str
    source_series_id: str
    units: str | None = None
    frequency: str | None = None
    category: str | None = None


class SeriesCreate(SeriesBase):
    pass


class SeriesRead(SeriesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ObservationBase(BaseModel):
    series_id: int
    observation_date: date
    value: float


class ObservationCreate(ObservationBase):
    pass


class ObservationRead(ObservationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
