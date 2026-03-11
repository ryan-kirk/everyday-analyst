from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import delete

from app.db.database import SessionLocal
from app.ingestion.http_client import request_json_with_retry, request_text_with_retry
from app.ingestion.storage import store_events
from app.models.event import Event

logger = logging.getLogger(__name__)

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred"
FED_FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
EVENT_SOURCE = "fred_release_calendar"
FOMC_SOURCE = "federal_reserve_fomc_calendar"

MONTH_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

YEAR_HEADER_RE = re.compile(r'<a id="\d+">(\d{4}) FOMC Meetings</a>', re.IGNORECASE)
MEETING_ROW_RE = re.compile(
    r'<div class="row fomc-meeting".*?'
    r'<div class="fomc-meeting__month[^>]*><strong>([A-Za-z]+)</strong></div>.*?'
    r'<div class="fomc-meeting__date[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class EventReleaseConfig:
    release_id: int
    event_name: str
    category: str
    importance_score: float
    summary_template: str


EVENT_RELEASES = [
    EventReleaseConfig(
        release_id=10,
        event_name="CPI Release",
        category="inflation",
        importance_score=0.9,
        summary_template="Consumer Price Index release date.",
    ),
    EventReleaseConfig(
        release_id=50,
        event_name="Nonfarm Payroll Release",
        category="labor",
        importance_score=0.92,
        summary_template="Employment Situation report release date (includes payrolls).",
    ),
    EventReleaseConfig(
        release_id=53,
        event_name="GDP Release",
        category="growth",
        importance_score=0.88,
        summary_template="Gross Domestic Product report release date.",
    ),
]


def _get_fred_api_key() -> str:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set. Add it to your environment before ingestion.")
    return api_key


def _fred_get(endpoint: str, **params: Any) -> dict[str, Any]:
    query_params = {"api_key": _get_fred_api_key(), "file_type": "json", **params}
    return request_json_with_retry("GET", f"{FRED_API_BASE_URL}{endpoint}", params=query_params)


def fetch_release_dates(
    release_id: int,
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    params: dict[str, str | int] = {
        "release_id": release_id,
        "sort_order": "asc",
        "limit": 10000,
    }
    payload = _fred_get("/release/dates", **params)
    raw_dates = payload.get("release_dates", [])

    result: list[date] = []
    for item in raw_dates:
        value = item.get("date")
        if not value:
            continue
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            logger.warning("Skipping malformed release date release_id=%s date=%s", release_id, value)
            continue
        if start is not None and parsed < start:
            continue
        if end is not None and parsed > end:
            continue
        result.append(parsed)
    return sorted(set(result))


def fetch_fomc_meeting_dates(
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    page = request_text_with_retry("GET", FED_FOMC_CALENDAR_URL)
    year_headers = list(YEAR_HEADER_RE.finditer(page))
    if not year_headers:
        logger.warning("No FOMC year headers found while parsing calendar")
        return []

    parsed_dates: set[date] = set()
    for index, match in enumerate(year_headers):
        year = int(match.group(1))
        section_start = match.end()
        section_end = year_headers[index + 1].start() if index + 1 < len(year_headers) else len(page)
        section_html = page[section_start:section_end]

        for row in MEETING_ROW_RE.finditer(section_html):
            month_text = row.group(1).strip().lower()
            date_text = re.sub(r"<[^>]+>", "", row.group(2)).strip()
            day_match = re.search(r"(\d{1,2})", date_text)
            month_value = MONTH_TO_NUMBER.get(month_text)
            if month_value is None or day_match is None:
                continue
            try:
                meeting_date = date(year, month_value, int(day_match.group(1)))
            except ValueError:
                continue
            if start is not None and meeting_date < start:
                continue
            if end is not None and meeting_date > end:
                continue
            parsed_dates.add(meeting_date)

    return sorted(parsed_dates)


def fetch_events(
    start: date | None = None,
    end: date | None = None,
) -> list[Event]:
    events: list[Event] = []

    fomc_dates = fetch_fomc_meeting_dates(start=start, end=end)
    for event_date in fomc_dates:
        events.append(
            Event(
                event_date=event_date,
                title="FOMC Meeting",
                summary="Scheduled FOMC meeting date from the Federal Reserve calendar.",
                category="fomc",
                source=FOMC_SOURCE,
                importance_score=0.95,
            )
        )
    logger.info("Fetched FOMC meeting dates count=%s", len(fomc_dates))

    for config in EVENT_RELEASES:
        release_dates = fetch_release_dates(release_id=config.release_id, start=start, end=end)
        for event_date in release_dates:
            events.append(
                Event(
                    event_date=event_date,
                    title=config.event_name,
                    summary=config.summary_template,
                    category=config.category,
                    source=EVENT_SOURCE,
                    importance_score=config.importance_score,
                )
            )
        logger.info(
            "Fetched event release category=%s release_id=%s count=%s",
            config.category,
            config.release_id,
            len(release_dates),
        )

    events.sort(key=lambda item: item.event_date)
    return events


def _remove_legacy_fomc_events() -> int:
    """Remove legacy FOMC rows from initial release-ID based ingestion."""
    with SessionLocal() as db:
        result = db.execute(
            delete(Event).where(
                Event.category == "fomc",
                Event.title == "FOMC Meeting",
                Event.source == EVENT_SOURCE,
            )
        )
        db.commit()
    return result.rowcount or 0


def ingest_events(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, int]:
    removed = _remove_legacy_fomc_events()
    if removed:
        logger.info("Removed legacy FOMC events count=%s", removed)

    events = fetch_events(start=start, end=end)
    result = store_events(events)
    logger.info(
        "Ingested events fetched=%s changed=%s inserted=%s updated=%s",
        result["fetched"],
        result["changed"],
        result["inserted"],
        result["updated"],
    )
    return result
