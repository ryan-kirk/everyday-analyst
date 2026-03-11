from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.preset import PresetRead
from app.services.preset_service import ensure_default_presets, list_presets

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=list[PresetRead])
def get_presets(db: Session = Depends(get_db)) -> list[PresetRead]:
    ensure_default_presets(db)
    return list_presets(db)
