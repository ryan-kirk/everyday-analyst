from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.database import engine
from app.ingestion.fred_client import fetch_series_observations, store_observations

INITIAL_SERIES_IDS = ["DGS2", "UNRATE"]


def main() -> None:
    Base.metadata.create_all(bind=engine)

    try:
        for source_series_id in INITIAL_SERIES_IDS:
            observations = fetch_series_observations(source_series_id)
            changed_count = store_observations(source_series_id, observations)
            print(
                f"Loaded {source_series_id}: fetched={len(observations)} "
                f"inserted_or_updated={changed_count}"
            )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
