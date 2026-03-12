from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.workspace import (
    SavedAnalysisBookmarkUpdate,
    SavedAnalysisCreate,
    SavedAnalysisRead,
    SavedAnalysisShareSettingsUpdate,
    SharedAnalysisRead,
    UserCreate,
    UserLoginRequest,
    UserNoteCreate,
    UserNoteRead,
    UserRead,
)
from app.services.workspace_service import (
    authenticate_user,
    build_share_path,
    create_saved_analysis,
    create_user,
    create_user_note,
    delete_saved_analysis,
    delete_saved_analysis_note,
    get_saved_analysis_for_user,
    get_series_by_id,
    get_shared_analysis_by_token,
    get_user_by_id,
    list_saved_analyses,
    list_saved_analysis_notes,
    set_saved_analysis_bookmark,
    set_saved_analysis_share_options,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.post("/users", response_model=UserRead, status_code=201)
def create_workspace_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if not payload.username.strip():
        raise HTTPException(status_code=400, detail="username must not be empty")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="name must not be empty")

    try:
        user = create_user(
            db=db,
            username=payload.username,
            password=payload.password,
            name=payload.name,
            email=payload.email,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="username or email already exists") from exc
    return UserRead.model_validate(user)


@router.get("/users/{user_id}", response_model=UserRead)
def get_workspace_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user not found: {user_id}")
    return UserRead.model_validate(user)


@router.post("/auth/login", response_model=UserRead)
def login_workspace_user(payload: UserLoginRequest, db: Session = Depends(get_db)) -> UserRead:
    if not payload.username.strip() or not payload.password:
        raise HTTPException(status_code=400, detail="username and password are required")

    user = authenticate_user(db=db, username=payload.username, password=payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    return UserRead.model_validate(user)


@router.post("/users/{user_id}/saved-analyses", response_model=SavedAnalysisRead, status_code=201)
def create_workspace_saved_analysis(
    user_id: int,
    payload: SavedAnalysisCreate,
    db: Session = Depends(get_db),
) -> SavedAnalysisRead:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user not found: {user_id}")

    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="title must not be empty")

    if get_series_by_id(db=db, series_id=payload.series_a_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"series not found for series_a_id={payload.series_a_id}",
        )
    if get_series_by_id(db=db, series_id=payload.series_b_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"series not found for series_b_id={payload.series_b_id}",
        )

    analysis = create_saved_analysis(
        db=db,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        series_a_id=payload.series_a_id,
        series_b_id=payload.series_b_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        event_category_filter=payload.event_category_filter,
        is_bookmarked=payload.is_bookmarked,
        share_include_notes=payload.share_include_notes,
    )
    hydrated = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis.id)
    if hydrated is None:
        raise HTTPException(status_code=500, detail="saved analysis could not be reloaded")

    return _to_saved_analysis_read(hydrated)


@router.get("/users/{user_id}/saved-analyses", response_model=list[SavedAnalysisRead])
def list_workspace_saved_analyses(
    user_id: int,
    bookmarked_only: bool = False,
    db: Session = Depends(get_db),
) -> list[SavedAnalysisRead]:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user not found: {user_id}")

    rows = list_saved_analyses(db=db, user_id=user_id, bookmarked_only=bookmarked_only)
    return [_to_saved_analysis_read(row) for row in rows]


@router.patch(
    "/users/{user_id}/saved-analyses/{analysis_id}/bookmark",
    response_model=SavedAnalysisRead,
)
def update_workspace_bookmark(
    user_id: int,
    analysis_id: int,
    payload: SavedAnalysisBookmarkUpdate,
    db: Session = Depends(get_db),
) -> SavedAnalysisRead:
    updated = set_saved_analysis_bookmark(
        db=db,
        user_id=user_id,
        analysis_id=analysis_id,
        is_bookmarked=payload.is_bookmarked,
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )

    reloaded = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=updated.id)
    if reloaded is None:
        raise HTTPException(status_code=500, detail="saved analysis could not be reloaded")
    return _to_saved_analysis_read(reloaded)


@router.patch(
    "/users/{user_id}/saved-analyses/{analysis_id}/share-settings",
    response_model=SavedAnalysisRead,
)
def update_workspace_share_settings(
    user_id: int,
    analysis_id: int,
    payload: SavedAnalysisShareSettingsUpdate,
    db: Session = Depends(get_db),
) -> SavedAnalysisRead:
    updated = set_saved_analysis_share_options(
        db=db,
        user_id=user_id,
        analysis_id=analysis_id,
        share_include_notes=payload.share_include_notes,
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )

    reloaded = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=updated.id)
    if reloaded is None:
        raise HTTPException(status_code=500, detail="saved analysis could not be reloaded")
    return _to_saved_analysis_read(reloaded)


@router.post(
    "/users/{user_id}/saved-analyses/{analysis_id}/notes",
    response_model=UserNoteRead,
    status_code=201,
)
def create_workspace_note(
    user_id: int,
    analysis_id: int,
    payload: UserNoteCreate,
    db: Session = Depends(get_db),
) -> UserNoteRead:
    if not payload.note_text.strip():
        raise HTTPException(status_code=400, detail="note_text must not be empty")

    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )

    note = create_user_note(
        db=db,
        user_id=user_id,
        saved_analysis_id=analysis_id,
        note_text=payload.note_text,
    )
    return UserNoteRead.model_validate(note)


@router.get(
    "/users/{user_id}/saved-analyses/{analysis_id}/notes",
    response_model=list[UserNoteRead],
)
def list_workspace_notes(
    user_id: int,
    analysis_id: int,
    db: Session = Depends(get_db),
) -> list[UserNoteRead]:
    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )

    rows = list_saved_analysis_notes(db=db, user_id=user_id, saved_analysis_id=analysis_id)
    return [UserNoteRead.model_validate(row) for row in rows]


@router.delete("/users/{user_id}/saved-analyses/{analysis_id}/notes/{note_id}", status_code=204)
def delete_workspace_note(
    user_id: int,
    analysis_id: int,
    note_id: int,
    db: Session = Depends(get_db),
) -> None:
    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )

    deleted = delete_saved_analysis_note(
        db=db,
        user_id=user_id,
        saved_analysis_id=analysis_id,
        note_id=note_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail=f"note not found: {note_id}")


@router.delete("/users/{user_id}/saved-analyses/{analysis_id}", status_code=204)
def delete_workspace_saved_analysis(
    user_id: int,
    analysis_id: int,
    db: Session = Depends(get_db),
) -> None:
    deleted = delete_saved_analysis(db=db, user_id=user_id, analysis_id=analysis_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"saved analysis not found: user_id={user_id}, analysis_id={analysis_id}",
        )


@router.get("/shared/{share_token}", response_model=SharedAnalysisRead)
def get_shared_analysis(share_token: str, db: Session = Depends(get_db)) -> SharedAnalysisRead:
    analysis = get_shared_analysis_by_token(db=db, share_token=share_token)
    if analysis is None:
        raise HTTPException(status_code=404, detail="shared analysis not found")

    notes = []
    if analysis.share_include_notes:
        notes = list_saved_analysis_notes(
            db=db,
            user_id=analysis.user_id,
            saved_analysis_id=analysis.id,
        )
    return SharedAnalysisRead(
        saved_analysis=_to_saved_analysis_read(analysis),
        notes=[UserNoteRead.model_validate(note) for note in notes],
        notes_shared=analysis.share_include_notes,
    )


def _to_saved_analysis_read(analysis) -> SavedAnalysisRead:
    return SavedAnalysisRead(
        id=analysis.id,
        user_id=analysis.user_id,
        title=analysis.title,
        description=analysis.description,
        series_a_id=analysis.series_a_id,
        series_b_id=analysis.series_b_id,
        start_date=analysis.start_date,
        end_date=analysis.end_date,
        event_category_filter=analysis.event_category_filter,
        is_bookmarked=analysis.is_bookmarked,
        share_include_notes=analysis.share_include_notes,
        share_token=analysis.share_token,
        share_path=build_share_path(analysis.share_token),
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
        series_a=analysis.series_a,
        series_b=analysis.series_b,
    )
