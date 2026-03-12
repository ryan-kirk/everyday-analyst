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
from app.db.schema_utils import ensure_event_columns, ensure_saved_analysis_columns, ensure_workspace_user_columns
from app.jobs.ingestion_jobs import (
    run_consumer_ingestion_job,
    run_housing_ingestion_job,
    run_market_ingestion_job,
    run_population_ingestion_job,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


def _print_domain_summary(label: str, result: dict) -> None:
    summary = result.get("summary", {})
    print(
        f"{label} load complete:",
        f"series={summary.get('series_count', 'n/a')}",
        f"succeeded={summary.get('succeeded', 'n/a')}",
        f"failed={summary.get('failed', 'n/a')}",
        f"optional_failures={summary.get('optional_failures', 'n/a')}",
        f"fetched={summary.get('fetched', 'n/a')}",
        f"changed={summary.get('changed', 'n/a')}",
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_event_columns(engine)
    ensure_workspace_user_columns(engine)
    ensure_saved_analysis_columns(engine)

    market_result = run_market_ingestion_job()
    housing_result = run_housing_ingestion_job()
    consumer_result = run_consumer_ingestion_job()
    population_result = run_population_ingestion_job()

    _print_domain_summary("Market", market_result)
    _print_domain_summary("Housing", housing_result)
    _print_domain_summary("Consumer", consumer_result)
    _print_domain_summary("Population", population_result)


if __name__ == "__main__":
    main()
