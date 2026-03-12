# Everyday Analyst

Everyday Analyst is an MVP decision-support app that helps non-expert users compare two public time series on a shared timeline, contextualize changes with notable macro events, and save/share analysis views.

## Current App Capabilities

- Normalized ingestion pipelines for economic and market time series.
- Event ingestion for FOMC dates and major release calendars.
- API endpoints for series, observations, events, compare, insights, presets, and workspace features.
- Deterministic insights that report overlap method, correlation, inflections, major moves, and nearby events.
- Preset analyst workflows (Fed Watch, Inflation vs Rates, Housing vs Mortgage Rates, Labor Market vs Rates, Growth vs Rates).
- User workspace features:
  - register/login
  - save comparison views
  - bookmark saved views
  - generate share links
  - add and delete notes tied to saved analyses
- Frontend charting with Chart.js including:
  - dual-axis compare view
  - event markers and vertical event lines
  - event category filter
  - insights panel
  - events table

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: SQLite (default local and current Fly volume deployment)
- Frontend: plain HTML + JavaScript + Chart.js
- Ingestion: requests/httpx-style retry helpers, script-based jobs, scheduler support

## Project Structure

```txt
everyday-analyst/
  backend/
    app/
      api/         # FastAPI route handlers
      db/          # engine/session/base/schema guard helpers
      ingestion/   # source clients + normalization + upsert storage
      jobs/        # orchestration jobs + scheduler loop
      models/      # SQLAlchemy ORM models
      schemas/     # Pydantic schemas
      services/    # business logic used by API routes
      main.py
    tests/         # unit + API integration-style tests
    requirements.txt
    alembic/       # migration placeholder
  frontend/
    index.html
    app.js
    terms.html
  scripts/         # ingestion entry points
```

## Environment Variables

Copy `.env.example` to `.env`, then set values:

```bash
cp .env.example .env
```

Expected keys:

```env
FRED_API_KEY=your_fred_key
BLS_API_KEY=your_bls_key_optional
DATABASE_URL=sqlite:///backend/everyday_analyst.db

# Optional comma-separated IDs for population/local domain expansion
POPULATION_MIGRATION_SERIES_IDS=NETMIGNACS006037,NETMIGNACS006059
COUNTY_HOUSING_PERMIT_SERIES_IDS=BPPRIV006037,BPPRIV006059
LOCAL_EMPLOYMENT_BLS_SERIES_IDS=LAUCN060590000000005,LAUCN360610000000005
```

Notes:
- `FRED_API_KEY` is required for FRED series and release-calendar ingestion.
- `BLS_API_KEY` is optional for BLS public API usage.
- If `DATABASE_URL` is omitted, backend defaults to SQLite at `backend/everyday_analyst.db`.
- Environment ID variables are optional. If omitted, default baseline population/local series are still ingested.
- ID format is source-native series IDs (not display names), comma-separated. IDs are uppercased and deduplicated automatically.

## Install and Run

1. Create/activate virtual environment and install dependencies:

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

3. Open app in browser:
- Recommended: backend serves frontend at `http://127.0.0.1:8000/`
- Optional separate frontend server:

```bash
cd frontend
python3 -m http.server 5500
```

## Ingestion Commands

Run from repo root:

```bash
python scripts/load_initial_data.py
python scripts/load_fred_series.py
python scripts/load_bls_series.py
python scripts/load_events.py
python scripts/load_domain_data.py
python scripts/run_ingestion_scheduler.py
```

`load_domain_data.py` runs the newer domain ingestors:
- market
- housing
- consumer
- population/local

## API Methods

### Core

- `GET /health`
- `GET /series`
- `GET /series/{series_id}/observations?start=&end=`
- `GET /events?start=&end=&category=`
- `GET /compare?series_a=&series_b=&start=&end=&event_category=`
- `GET /insights?series_a=&series_b=&start=&end=`
- `GET /presets`

`/compare` response includes:
- `series_a` metadata
- `series_b` metadata
- aligned `observations`
- in-range `events` (respecting optional category filter)

### Workspace

- `POST /workspace/users` (register)
- `POST /workspace/auth/login` (login)
- `GET /workspace/users/{user_id}`
- `POST /workspace/users/{user_id}/saved-analyses`
- `GET /workspace/users/{user_id}/saved-analyses`
- `PATCH /workspace/users/{user_id}/saved-analyses/{analysis_id}/bookmark`
- `PATCH /workspace/users/{user_id}/saved-analyses/{analysis_id}/share-settings`
- `POST /workspace/users/{user_id}/saved-analyses/{analysis_id}/notes`
- `GET /workspace/users/{user_id}/saved-analyses/{analysis_id}/notes`
- `DELETE /workspace/users/{user_id}/saved-analyses/{analysis_id}/notes/{note_id}`
- `GET /workspace/shared/{share_token}`

## Backend Modules

### API Layer (`backend/app/api`)
- `health.py`: liveness endpoint.
- `series.py`: series list + single series observations.
- `events.py`: range/category-filtered events.
- `compare.py`: dual-series alignment + events overlay payload.
- `insights.py`: insight payload endpoint.
- `presets.py`: preset listing endpoint.
- `workspace.py`: user/saved-analysis/note/share routes.

### Service Layer (`backend/app/services`)
- `series_service.py`: series metadata and observation queries.
- `event_service.py`: event queries by range/category.
- `compare_service.py`: shared-date alignment and compare payload assembly.
- `insight_service.py`: deterministic metrics, inflections, movements, and narratives.
- `preset_service.py`: default preset provisioning and retrieval.
- `workspace_service.py`: user auth + saved analysis + note/share logic.

### Models (`backend/app/models`)
- `Series`
- `Observation`
- `Event`
- `Preset`
- `User`
- `SavedAnalysis`
- `UserNote`

### Schemas (`backend/app/schemas`)
- `series.py`
- `event.py`
- `compare.py`
- `insights.py`
- `preset.py`
- `workspace.py`

### DB Layer (`backend/app/db`)
- `database.py`: engine/session setup.
- `base.py`: SQLAlchemy base.
- `schema_utils.py`: compatibility guards for iterative schema changes.

### Ingestion (`backend/app/ingestion`)
- Core connectors:
  - `fred_client.py`
  - `bls_client.py`
  - `event_client.py`
  - `stooq_client.py`
- Domain connectors:
  - `market_client.py`
  - `housing_client.py`
  - `consumer_client.py`
  - `population_client.py`
- Shared ingestion framework:
  - `domain_pipeline.py` (source dispatch + metadata overrides + optional failure handling)
  - `storage.py` (normalized upserts)
  - `http_client.py` (retry-enabled HTTP helpers)

### Jobs (`backend/app/jobs`)
- `ingestion_jobs.py`: orchestrates source and domain ingestion jobs.
- `scheduler.py`: periodic ingestion loop wrapper.

## Data Sources

### FRED (Federal Reserve Economic Data)
- Core macro/rates: `DGS2`, `DGS10`, `T10Y2Y`, `UNRATE`, `PAYEMS`, `CPIAUCSL`, `PCEPI`, `INDPRO`, `MORTGAGE30US`, `CSUSHPISA`, `HOUST`
- Market/commodities additions: `SP500`, `VIXCLS`, `NASDAQCOM`, `DCOILWTICO`, `PCOPPUSDM`
- Housing additions: `USSTHPI`, `PERMIT`, optional `M0264AUSM500NNBR`
- Consumer additions: `RSAFS`, `RRSFS`, `UMCSENT`, `REVOLSL`, optional `CCLACBW027SBOG`
- Population/local examples: `POPTHM`, optional `NETMIGNACS006037`, optional county permits via `BPPRIV...`

### BLS Public API
- Baseline labor series:
  - `LNS14000000` (Unemployment Rate)
  - `CES0000000001` (Total Nonfarm Payrolls)
- Optional local employment via env IDs (examples use `LAUCN...`).

### Federal Reserve Board Website
- FOMC meeting dates parsed from:
  - `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`

### Stooq
- ETF price history ingestion used for treasury ETF examples:
  - `IEF`
  - `TLT`

## Unit Tests

Run all tests:

```bash
cd backend
python -m unittest -v
```

Current test modules include:
- `test_health.py`
- `test_compare.py`
- `test_events_api.py`
- `test_fred_client.py`
- `test_bls_client.py`
- `test_event_client.py`
- `test_insights.py`
- `test_presets_api.py`
- `test_workspace_api.py`
- `test_stooq_client.py`
- `test_domain_pipeline.py`
- `test_market_client.py`
- `test_housing_client.py`
- `test_consumer_client.py`
- `test_population_client.py`
- `test_ingestion_jobs.py`

Coverage focus:
- core API behavior
- workspace API behavior
- source normalization and parsing
- domain pipeline behavior (overrides, optional/required failures)
- storage upsert behavior

## Frontend Capabilities

Current UI (`frontend/index.html` + `frontend/app.js`) supports:
- preset selector + auto-apply behavior
- series A/B selectors
- date range controls
- event category filtering
- comparison chart with two datasets and optional dual-axis rendering
- event markers + vertical event lines + tooltip event context
- insights panel:
  - narrative summary
  - series context with source links
  - inflection points
  - major movements
- events table for selected range
- workspace panel:
  - user login/register/logout
  - save/bookmark/share analysis views
  - saved view list load/refresh
  - notes CRUD for saved analyses
- terms page link (`/terms.html` when served by FastAPI static hosting)

## Fly.io Deployment (Initial)

This repository is currently configured as a single Fly app serving:
- FastAPI API routes
- static frontend from the same container

Deployment files:
- `fly.toml`
- `Dockerfile`

Architecture note:
- Current production DB setup is SQLite on Fly volume (`/data/everyday_analyst.db`).
- This is intentionally single-machine until migration to Postgres.

Deploy summary:

```bash
fly auth login
fly launch --no-deploy --copy-config --name everyday-analyst --region ord
fly volumes create data --region ord --size 1
fly secrets set FRED_API_KEY=your_fred_api_key
fly secrets set BLS_API_KEY=your_bls_api_key_optional
fly deploy
```

Load data inside deployed machine:

```bash
fly ssh console -C "python /app/scripts/load_initial_data.py"
fly ssh console -C "python /app/scripts/load_domain_data.py"
fly ssh console -C "python /app/scripts/load_events.py"
```

## Compliance, Licenses, and Terms Constraints

This section is an engineering summary and is not legal advice.

### Required disclosures

- No endorsement: use of this app does not imply endorsement of any product, issuer, service, or data provider.
- Not financial advice: this app is informational/educational only and does not provide investment, legal, tax, or professional advice.
- FRED required notice:
  - `This product uses the FRED(R) API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.`

### Software license summary

Current dependency profile is primarily permissive licenses:
- FastAPI: MIT
- Uvicorn: BSD-3-Clause
- SQLAlchemy: MIT
- pandas: BSD-3-Clause
- requests: Apache-2.0
- python-dotenv: BSD-3-Clause
- httpx: BSD-3-Clause
- Chart.js: MIT

Engineering obligations:
- Preserve copyright/license notices when redistributing.
- Include required license texts as needed.
- Do not imply upstream endorsement.
- Respect "as-is" warranty disclaimers.

### Data/API terms constraints

FRED API (St. Louis Fed):
- Terms: https://fred.stlouisfed.org/docs/api/terms_of_use.html
- Keep required FRED attribution/disclaimer.
- Respect third-party rights for copyrighted series.
- Do not imply Federal Reserve Bank endorsement.

BLS Public API:
- Terms: https://www.bls.gov/developers/termsOfService.htm
- API features/limits: https://www.bls.gov/bls/api_features.htm
- Include BLS disclaimer when presenting BLS-derived analysis:
  - `BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.`
- Respect documented usage limits and branding constraints.

Federal Reserve Board website materials (FOMC calendar source):
- Disclaimer: https://www.federalreserve.gov/disclaimer.htm
- Attribute source, avoid restricted insignia/logo usage, and respect non-Board third-party rights where marked.

Stooq (ETF market data source):
- Site: https://stooq.com/
- Terms/Regulations: https://stooq.pl/regulamin/
- Privacy: https://stooq.pl/polityka_prywatnosci/
- Review and comply with current usage and redistribution restrictions before commercial/public redistribution.

Google Fonts (frontend hosted font usage):
- Terms: https://developers.google.com/fonts/terms
- FAQ: https://developers.google.com/fonts/faq
- Privacy FAQ: https://developers.google.com/fonts/faq/privacy

## Terms of Service Page

The app now includes a dedicated terms page at:
- `frontend/terms.html`

When served by FastAPI static hosting, this is available at:
- `/terms.html`

Keep this page aligned with any data-source, licensing, or compliance changes.
