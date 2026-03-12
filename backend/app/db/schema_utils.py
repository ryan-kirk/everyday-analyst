from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_event_columns(engine: Engine) -> None:
    """Best-effort schema guard for event fields during early MVP iterations."""
    inspector = inspect(engine)
    if not inspector.has_table("events"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("events")}

    with engine.begin() as connection:
        if "importance_score" not in existing_columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN importance_score FLOAT"))


def ensure_workspace_user_columns(engine: Engine) -> None:
    """Best-effort schema guard for user auth fields during early MVP iterations."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    with engine.begin() as connection:
        if "username" not in existing_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(120)"))
        if "password_hash" not in existing_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))

        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))


def ensure_saved_analysis_columns(engine: Engine) -> None:
    """Best-effort schema guard for saved analysis sharing fields."""
    inspector = inspect(engine)
    if not inspector.has_table("saved_analyses"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("saved_analyses")}

    with engine.begin() as connection:
        if "share_include_notes" not in existing_columns:
            connection.execute(
                text("ALTER TABLE saved_analyses ADD COLUMN share_include_notes BOOLEAN DEFAULT 0")
            )
