from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from app.jobs.ingestion_jobs import run_full_ingestion_job

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Simple interval scheduler for ingestion jobs."""

    def __init__(self, interval_minutes: int = 360) -> None:
        self.interval_minutes = interval_minutes
        self._stop_event = threading.Event()

    def run_once(self) -> None:
        started_at = datetime.now(tz=timezone.utc)
        logger.info("Running scheduled ingestion cycle started_at=%s", started_at.isoformat())
        try:
            run_full_ingestion_job()
            logger.info("Scheduled ingestion cycle completed")
        except Exception:
            logger.exception("Scheduled ingestion cycle failed")

    def run_forever(self) -> None:
        logger.info(
            "Ingestion scheduler started interval_minutes=%s",
            self.interval_minutes,
        )
        while not self._stop_event.is_set():
            self.run_once()
            wait_seconds = self.interval_minutes * 60
            if self._stop_event.wait(timeout=wait_seconds):
                break
        logger.info("Ingestion scheduler stopped")

    def stop(self) -> None:
        self._stop_event.set()

