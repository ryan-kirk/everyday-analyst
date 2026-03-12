from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.series import SeriesRead


class UserBase(BaseModel):
    username: str
    name: str
    email: str | None = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLoginRequest(BaseModel):
    username: str
    password: str


class SavedAnalysisBase(BaseModel):
    title: str
    description: str | None = None
    series_a_id: int
    series_b_id: int
    start_date: date | None = None
    end_date: date | None = None
    event_category_filter: str | None = None


class SavedAnalysisCreate(SavedAnalysisBase):
    is_bookmarked: bool = False
    share_include_notes: bool = False


class SavedAnalysisBookmarkUpdate(BaseModel):
    is_bookmarked: bool


class SavedAnalysisShareSettingsUpdate(BaseModel):
    share_include_notes: bool


class SavedAnalysisRead(SavedAnalysisBase):
    id: int
    user_id: int
    is_bookmarked: bool
    share_include_notes: bool
    share_token: str
    share_path: str
    created_at: datetime
    updated_at: datetime
    series_a: SeriesRead | None = None
    series_b: SeriesRead | None = None

    model_config = ConfigDict(from_attributes=True)


class UserNoteBase(BaseModel):
    note_text: str


class UserNoteCreate(UserNoteBase):
    pass


class UserNoteRead(UserNoteBase):
    id: int
    user_id: int
    saved_analysis_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SharedAnalysisRead(BaseModel):
    saved_analysis: SavedAnalysisRead
    notes: list[UserNoteRead]
    notes_shared: bool
