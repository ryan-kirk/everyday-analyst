from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.saved_analysis import SavedAnalysis
from app.models.series import Series
from app.models.user import User
from app.models.user_note import UserNote


PBKDF2_ITERATIONS = 260000


def create_user(
    db: Session,
    username: str,
    password: str,
    name: str,
    email: str | None = None,
) -> User:
    normalized_email = email.strip().lower() if email and email.strip() else None
    user = User(
        username=username.strip().lower(),
        password_hash=hash_password(password),
        name=name.strip(),
        email=normalized_email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def get_user_by_username(db: Session, username: str) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.username == username.strip().lower())
    return db.scalar(stmt)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db=db, username=username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_series_by_id(db: Session, series_id: int) -> Series | None:
    stmt: Select[tuple[Series]] = select(Series).where(Series.id == series_id)
    return db.scalar(stmt)


def create_saved_analysis(
    db: Session,
    user_id: int,
    title: str,
    description: str | None,
    series_a_id: int,
    series_b_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    event_category_filter: str | None = None,
    is_bookmarked: bool = False,
    share_include_notes: bool = False,
) -> SavedAnalysis:
    normalized_title = title.strip()
    existing = get_saved_analysis_by_title(db=db, user_id=user_id, title=normalized_title)
    if existing is not None:
        existing.title = normalized_title
        existing.description = description.strip() if description else None
        existing.series_a_id = series_a_id
        existing.series_b_id = series_b_id
        existing.start_date = start_date
        existing.end_date = end_date
        existing.event_category_filter = event_category_filter.strip() if event_category_filter else None
        existing.is_bookmarked = is_bookmarked
        existing.share_include_notes = share_include_notes
        db.commit()
        db.refresh(existing)
        return existing

    analysis = SavedAnalysis(
        user_id=user_id,
        title=normalized_title,
        description=description.strip() if description else None,
        series_a_id=series_a_id,
        series_b_id=series_b_id,
        start_date=start_date,
        end_date=end_date,
        event_category_filter=event_category_filter.strip() if event_category_filter else None,
        is_bookmarked=is_bookmarked,
        share_include_notes=share_include_notes,
        share_token=_generate_unique_share_token(db),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_saved_analysis_by_title(db: Session, user_id: int, title: str) -> SavedAnalysis | None:
    normalized = title.strip().lower()
    if not normalized:
        return None
    stmt: Select[tuple[SavedAnalysis]] = (
        select(SavedAnalysis)
        .where(
            SavedAnalysis.user_id == user_id,
            func.lower(SavedAnalysis.title) == normalized,
        )
        .order_by(SavedAnalysis.updated_at.desc(), SavedAnalysis.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def list_saved_analyses(
    db: Session,
    user_id: int,
    bookmarked_only: bool = False,
) -> list[SavedAnalysis]:
    stmt: Select[tuple[SavedAnalysis]] = (
        select(SavedAnalysis)
        .where(SavedAnalysis.user_id == user_id)
        .options(
            joinedload(SavedAnalysis.series_a),
            joinedload(SavedAnalysis.series_b),
        )
        .order_by(SavedAnalysis.updated_at.desc(), SavedAnalysis.id.desc())
    )
    if bookmarked_only:
        stmt = stmt.where(SavedAnalysis.is_bookmarked.is_(True))
    return list(db.scalars(stmt).all())


def get_saved_analysis_for_user(db: Session, user_id: int, analysis_id: int) -> SavedAnalysis | None:
    stmt: Select[tuple[SavedAnalysis]] = (
        select(SavedAnalysis)
        .where(
            SavedAnalysis.id == analysis_id,
            SavedAnalysis.user_id == user_id,
        )
        .options(
            joinedload(SavedAnalysis.series_a),
            joinedload(SavedAnalysis.series_b),
        )
    )
    return db.scalar(stmt)


def set_saved_analysis_bookmark(
    db: Session,
    user_id: int,
    analysis_id: int,
    is_bookmarked: bool,
) -> SavedAnalysis | None:
    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        return None

    analysis.is_bookmarked = is_bookmarked
    db.commit()
    db.refresh(analysis)
    return analysis


def set_saved_analysis_share_options(
    db: Session,
    user_id: int,
    analysis_id: int,
    share_include_notes: bool,
) -> SavedAnalysis | None:
    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        return None

    analysis.share_include_notes = share_include_notes
    db.commit()
    db.refresh(analysis)
    return analysis


def create_user_note(db: Session, user_id: int, saved_analysis_id: int, note_text: str) -> UserNote:
    note = UserNote(
        user_id=user_id,
        saved_analysis_id=saved_analysis_id,
        note_text=note_text.strip(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_saved_analysis_notes(db: Session, user_id: int, saved_analysis_id: int) -> list[UserNote]:
    stmt: Select[tuple[UserNote]] = (
        select(UserNote)
        .where(
            UserNote.user_id == user_id,
            UserNote.saved_analysis_id == saved_analysis_id,
        )
        .order_by(UserNote.created_at.asc(), UserNote.id.asc())
    )
    return list(db.scalars(stmt).all())


def delete_saved_analysis_note(
    db: Session,
    user_id: int,
    saved_analysis_id: int,
    note_id: int,
) -> bool:
    stmt: Select[tuple[UserNote]] = select(UserNote).where(
        UserNote.id == note_id,
        UserNote.user_id == user_id,
        UserNote.saved_analysis_id == saved_analysis_id,
    )
    note = db.scalar(stmt)
    if note is None:
        return False

    db.delete(note)
    db.commit()
    return True


def delete_saved_analysis(
    db: Session,
    user_id: int,
    analysis_id: int,
) -> bool:
    analysis = get_saved_analysis_for_user(db=db, user_id=user_id, analysis_id=analysis_id)
    if analysis is None:
        return False

    db.delete(analysis)
    db.commit()
    return True


def get_shared_analysis_by_token(db: Session, share_token: str) -> SavedAnalysis | None:
    stmt: Select[tuple[SavedAnalysis]] = (
        select(SavedAnalysis)
        .where(SavedAnalysis.share_token == share_token)
        .options(
            joinedload(SavedAnalysis.series_a),
            joinedload(SavedAnalysis.series_b),
        )
    )
    return db.scalar(stmt)


def build_share_path(share_token: str) -> str:
    return f"/workspace/shared/{share_token}"


def _generate_unique_share_token(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(16)
        stmt: Select[tuple[int]] = select(SavedAnalysis.id).where(SavedAnalysis.share_token == token)
        if db.scalar(stmt) is None:
            return token


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected)
