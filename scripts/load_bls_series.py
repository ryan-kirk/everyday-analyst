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
from app.jobs.ingestion_jobs import DEFAULT_BLS_SERIES_IDS, run_bls_ingestion_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    result = run_bls_ingestion_job(series_ids=DEFAULT_BLS_SERIES_IDS)
    summary = result["summary"]
    print(
        "BLS load complete:",
        f"series={summary['series_count']}",
        f"fetched={summary['fetched']}",
        f"changed={summary['changed']}",
    )


if __name__ == "__main__":
    main()

