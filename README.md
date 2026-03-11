# Everyday Analyst

Everyday Analyst is an MVP decision-support app for comparing two public time series on a shared timeline and aligning them with notable macro events.

## Current App Capabilities

- Ingests normalized time series data from FRED and BLS.
- Ingests notable events (FOMC, CPI releases, NFP releases, GDP releases).
- Serves API endpoints for series, observations, events, and two-series comparison.
- Renders a browser-based chart comparison UI with:
  - two series selectors
  - date range controls
  - event category filter
  - event markers and vertical event-date lines
  - tooltips containing event details

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: SQLite (default local dev)
- Frontend: plain HTML + JavaScript + Chart.js
- Ingestion: requests + retry logic, script-driven and scheduler-ready

## Project Structure

```txt
everyday-analyst/
  backend/
    app/
      api/         # FastAPI routes
      db/          # engine/session/base/schema helpers
      ingestion/   # source clients + normalization/store utilities
      jobs/        # ingestion jobs + scheduler
      models/      # SQLAlchemy ORM models
      schemas/     # Pydantic response/request schemas
      services/    # business logic used by API handlers
      main.py
    tests/         # unit/integration-style tests
    requirements.txt
    alembic/       # migration placeholder
  frontend/
    index.html
    app.js
  scripts/         # ingestion entry points
```

## Environment Variables

Create a root `.env` file with:

```env
FRED_API_KEY=your_fred_key
BLS_API_KEY=your_bls_key_optional
DATABASE_URL=sqlite:///backend/everyday_analyst.db
```

Notes:
- `FRED_API_KEY` is required for FRED data/event ingestion.
- `BLS_API_KEY` is optional for the public BLS API.
- If `DATABASE_URL` is omitted, backend defaults to SQLite at `backend/everyday_analyst.db`.

## Install and Run

1. Create/activate a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Run the backend API:

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

3. Open the app:
- Option A (recommended): backend serves frontend at `http://127.0.0.1:8000/`
- Option B: serve frontend separately:

```bash
cd frontend
python3 -m http.server 5500
```

If running Option B, set `API Base URL` in the UI to `http://127.0.0.1:8000`.

## API Methods

### `GET /health`
- Returns service liveness.
- Response:

```json
{"status":"ok"}
```

### `GET /series`
- Returns all available normalized time series metadata.

### `GET /series/{series_id}/observations?start=&end=`
- Returns observations for one series.
- Query params:
  - `start` (optional, `YYYY-MM-DD`)
  - `end` (optional, `YYYY-MM-DD`)

### `GET /events?start=&end=&category=`
- Returns events in a date range.
- Query params:
  - `start` (optional)
  - `end` (optional)
  - `category` (optional; examples: `fomc`, `labor`, `inflation`, `growth`)

### `GET /compare?series_a=&series_b=&start=&end=&event_category=`
- Returns aligned observations for two series and related events in range.
- Query params:
  - `series_a` (required, internal series id)
  - `series_b` (required, internal series id)
  - `start` (optional)
  - `end` (optional)
  - `event_category` (optional; supports repeated params or comma-separated values)

Example compare response shape:

```json
{
  "series_a": {"id": 1, "name": "...", "source": "...", "source_series_id": "..."},
  "series_b": {"id": 2, "name": "...", "source": "...", "source_series_id": "..."},
  "observations": [
    {"date": "2026-03-01", "value_a": 3.4, "value_b": 4.1}
  ],
  "events": [
    {
      "id": 12,
      "event_date": "2026-03-06",
      "title": "Nonfarm Payroll Release",
      "summary": "Employment Situation report release date (includes payrolls).",
      "category": "labor",
      "source": "fred_release_calendar",
      "importance_score": 0.92
    }
  ]
}
```

## Backend Modules

### API Layer (`backend/app/api`)
- `health.py`: liveness endpoint.
- `series.py`: series list and single-series observations.
- `events.py`: date/category filtered event retrieval.
- `compare.py`: two-series aligned comparison + in-range events.

### Service Layer (`backend/app/services`)
- `series_service.py`: DB query logic for series and observations.
- `event_service.py`: DB query logic for event ranges/categories.
- `compare_service.py`: date alignment and compare event retrieval.

### Models (`backend/app/models`)
- `Series`: source metadata for each time series.
- `Observation`: normalized dated values linked to `Series`.
- `Event`: notable event timeline data with category and importance.

### Schemas (`backend/app/schemas`)
- Pydantic schemas for `series`, `event`, and `compare` responses.

### DB Layer (`backend/app/db`)
- `database.py`: engine/session setup and dependency injection.
- `base.py`: declarative base.
- `schema_utils.py`: lightweight schema guard for iterative local changes.

### Ingestion (`backend/app/ingestion`)
- `fred_client.py`: FRED series metadata + observations ingestion.
- `bls_client.py`: BLS timeseries normalization to monthly observations.
- `event_client.py`: event ingestion (FOMC calendar + FRED release dates).
- `http_client.py`: retry-enabled HTTP helpers.
- `storage.py`: upsert logic for normalized `Series`, `Observation`, and `Event` records.

### Jobs (`backend/app/jobs`)
- `ingestion_jobs.py`: orchestrates FRED/BLS/event ingestion runs.
- `scheduler.py`: interval scheduler wrapper for recurring ingestion.

## Data Sources

### FRED (Federal Reserve Economic Data)
- Time series ingested:
  - `DGS2`, `DGS10`, `T10Y2Y`, `UNRATE`, `PAYEMS`, `CPIAUCSL`,
  - `PCEPI`, `INDPRO`, `MORTGAGE30US`, `CSUSHPISA`, `HOUST`
- Event release calendars used for:
  - CPI releases
  - Nonfarm Payroll releases
  - GDP releases

### BLS Public API
- Baseline labor series ingested:
  - `LNS14000000` (Unemployment Rate)
  - `CES0000000001` (Total Nonfarm Payrolls)

### Federal Reserve
- FOMC meeting dates parsed from:
  - `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`

## Ingestion Scripts

Run from repo root:

```bash
python scripts/load_initial_data.py
python scripts/load_fred_series.py
python scripts/load_bls_series.py
python scripts/load_events.py
python scripts/run_ingestion_scheduler.py
```

## Unit Tests

Run all tests:

```bash
cd backend
python -m unittest -v
```

Current test modules:
- `test_health.py`
- `test_compare.py`
- `test_events_api.py`
- `test_fred_client.py`
- `test_bls_client.py`
- `test_event_client.py`

Coverage focus:
- API behavior (`/health`, `/compare`, `/events`)
- normalization/parsing for FRED, BLS, and event ingestion
- storage upsert behavior for core ingestion paths

## Frontend Capabilities

Current UI (`frontend/index.html` + `frontend/app.js`):
- API base URL input (with local dev auto-detection)
- Series A / Series B selection
- Date range selection
- Event category filter
- Comparison line chart with aligned timeline
- Event overlays:
  - marker points
  - vertical date lines
  - hover tooltip event details

## Compliance Note for FRED Data

Place this notice prominently in the application:

`This product uses the FRED(R) API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.`

Copyrighted FRED series contain "Copyright" in notes metadata.

## License and Terms Constraints

This section summarizes practical constraints for the software libraries and external data/services currently used by this repository. It is an engineering checklist, not legal advice.

### Disclosure

- No endorsement: Use of this application does not imply endorsement of any product, service, issuer, or data provider.
- Not financial advice: This application is for informational and educational purposes only and does not constitute financial, investment, legal, or tax advice.

### Software licenses used in this project

Current dependency set in this repo is permissive-license heavy:

- FastAPI: MIT
- Uvicorn: BSD-3-Clause
- SQLAlchemy: MIT
- pandas: BSD-3-Clause
- requests: Apache-2.0
- python-dotenv: BSD-3-Clause
- httpx: BSD-3-Clause
- Chart.js (CDN): MIT

Practical obligations for these licenses:

- Preserve copyright and license notices when redistributing software.
- Include required license text in distributions where applicable.
- Do not imply endorsement by upstream project maintainers.
- Accept "as-is" warranty disclaimers in those licenses.

### Data/API terms constraints

#### FRED API (St. Louis Fed)

Source: https://fred.stlouisfed.org/docs/api/terms_of_use.html

Key constraints relevant to this app:

- The required notice must be shown in the application:
  - `This product uses the FRED(R) API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.`
- Do not imply Fed endorsement or use restricted Fed trademarks/logos.
- Respect third-party rights on copyrighted FRED series and obtain permission when required.
- Keep and do not remove proprietary notices attached to data.
- Comply with any API limits and policy updates.

#### BLS Public API

Sources:
- https://www.bls.gov/developers/termsOfService.htm
- https://www.bls.gov/bls/api_features.htm

Key constraints relevant to this app:

- Cite the retrieval date for BLS data.
- Include the BLS disclaimer text:
  - `BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.`
- Do not use BLS logos on non-BLS products.
- Do not modify/falsely represent BLS content while citing it as BLS.
- Respect usage limits (for API v2 docs: max 50 series/request, max 500 queries/day, max 20 years/request).

#### Federal Reserve Board website data (FOMC calendar)

Source: https://www.federalreserve.gov/disclaimer.htm

Key constraints relevant to this app:

- Unless otherwise indicated, Board information is public domain and may be copied/distributed.
- Cite the Board as the source.
- Materials marked as non-Board/copyrighted require permission from the original source.
- Board seals/logos and related official insignia cannot be used without written permission.
- Board disclaims warranties; data should be used with caution.

### Frontend CDN and hosted asset terms

#### Chart.js CDN asset

Source: https://github.com/chartjs/Chart.js

- Chart.js is MIT-licensed.
- If vendoring or redistributing, preserve MIT license notice.

#### Google Fonts API (Space Grotesk)

Sources:
- https://developers.google.com/fonts/terms
- https://developers.google.com/fonts/faq
- https://developers.google.com/fonts/faq/privacy

Key constraints relevant to this app:

- Using the Google Fonts API means agreeing to Google APIs Terms of Service.
- Google Fonts are open source and generally allowed for commercial use under each font's specific license.
- Embedding hosted fonts sends user requests to Google servers (including IP/user-agent/referrer handling described in Google's privacy FAQ).
- To avoid this data flow, self-host font files.

## Known Follow-Up Work

- Deploy to Fly.io (`flyctl`).
- Add admin endpoint/CLI options for incremental backfills.
- Expand abuse protections/rate-limiting/caching strategy.
- Add richer metadata and explanatory insights per series.
- Add more tests for modules and edge-case ingestion failures.
