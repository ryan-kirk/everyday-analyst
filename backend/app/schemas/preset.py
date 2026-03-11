from pydantic import BaseModel, ConfigDict


class PresetRead(BaseModel):
    id: int
    name: str
    series_a: str
    series_b: str
    recommended_date_range: str
    description: str

    model_config = ConfigDict(from_attributes=True)
