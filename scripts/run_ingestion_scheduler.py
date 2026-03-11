from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.database import engine
from app.db.schema_utils import ensure_event_columns
from app.jobs.scheduler import IngestionScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    interval_minutes = 360
    Base.metadata.create_all(bind=engine)
    ensure_event_columns(engine)
    scheduler = IngestionScheduler(interval_minutes=interval_minutes)

    def _handle_signal(*_: object) -> None:
        logger.info("Received termination signal, stopping scheduler")
        scheduler.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("Starting ingestion scheduler interval_minutes=%s", interval_minutes)
    scheduler.run_forever()


if __name__ == "__main__":
    main()
