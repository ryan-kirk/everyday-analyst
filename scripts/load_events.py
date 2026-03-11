from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.database import engine
from app.db.schema_utils import ensure_event_columns
from app.jobs.ingestion_jobs import run_event_ingestion_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_event_columns(engine)
    result = run_event_ingestion_job()
    summary = result["summary"]
    print(
        "Events load complete:",
        f"fetched={summary['fetched']}",
        f"changed={summary['changed']}",
        f"inserted={summary['inserted']}",
        f"updated={summary['updated']}",
    )


if __name__ == "__main__":
    main()

