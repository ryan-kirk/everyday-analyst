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

