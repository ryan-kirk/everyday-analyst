from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.event import EventRead
from app.services.event_service import list_event_categories, list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
def get_events(
    start: date | None = None,
    end: date | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[EventRead]:
    return list_events(db=db, start=start, end=end, category=category)


@router.get("/categories", response_model=list[str])
def get_event_categories(db: Session = Depends(get_db)) -> list[str]:
    return list_event_categories(db=db)
