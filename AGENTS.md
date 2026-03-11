# AGENTS.md

## Project Name
Everyday Analyst

## Product Purpose
Everyday Analyst is a decision-support application for non-expert users. Its purpose is to help everyday people understand how current events may relate to real-world trends by comparing time series data with a timeline of noteworthy events.

The initial product focus is:
- helping users compare **two time series**
- placing those series in the context of **recent notable events**
- starting with a narrow, practical domain: **recent events and their relationship to U.S. short-term bond prices**
- incorporating labor and macroeconomic context where useful, beginning with **BLS employment data** and potentially expanding to **FRED**, **U.S. Treasury**, and other public data sources

This is **not** intended to be a full financial trading platform or a high-frequency analytics system. The goal is lightweight, understandable, consumer-friendly analysis that improves day-to-day judgment.

---

## Core User Problem
Most people do not have the time, tools, or analytical training to connect:
1. what is happening in the news,
2. what is changing in the economy,
3. and how those changes show up in observable data.

Everyday Analyst should reduce that gap by turning public data and recent events into simple visual comparisons and plain-language explanations.

Example user questions:
- "Did recent jobs data affect short-term Treasury yields?"
- "How did bond prices move after a major Fed-related event?"
- "What events happened around the same time this series changed direction?"
- "What changed in the last 30 days that might explain movement in this chart?"

---

## Initial Product Scope
Build a web application that:
1. retrieves one or more public time series
2. retrieves a list of recent noteworthy events
3. aligns events to a timeline
4. lets users compare two series visually
5. generates a simple explanation layer describing possible relationships between the series and recent events

Initial comparison target:
- U.S. short-term bond-related data
- employment or macroeconomic data as context
- recent U.S. economic / policy / market-related events

---

## Non-Goals (for now)
Do **not** optimize for the following in the first phase:
- brokerage integration
- portfolio management
- personalized investment advice
- advanced forecasting
- complex ML pipelines
- multi-tenant enterprise architecture
- real-time streaming infrastructure
- mobile app development
- social/community features

The first goal is to establish a reliable, interpretable MVP.

---

## Product Principles
When making design or implementation choices, prioritize these principles:

1. **Clarity over complexity**  
   Prefer simple visualizations and understandable explanations.

2. **Explainability over sophistication**  
   Users should be able to see why something is being shown.

3. **Narrow scope over broad ambition**  
   Win one focused use case before expanding.

4. **Deterministic pipelines over agentic magic**  
   For early versions, favor auditable ETL and rule-based annotation.

5. **Public data first**  
   Use stable, well-documented public sources wherever possible.

6. **Fast iteration**  
   Choose tools and architecture that allow quick local development and deployment.

---

## Target User
Initial target user:
- a curious, non-expert individual
- interested in understanding the economy, markets, or public events
- wants decision support, not technical jargon
- values practical insights more than academic completeness

Possible future users:
- retail investors
- homebuyers
- small business owners
- local decision-makers
- journalists / researchers
- students

---

## MVP User Experience
The MVP should support a basic workflow like this:

1. User opens the application
2. User selects two time series to compare
3. Application loads chart(s) with shared timeline
4. Application overlays or lists noteworthy recent events
5. Application provides a concise narrative summary such as:
   - what changed
   - when it changed
   - what events occurred nearby in time
   - what might plausibly explain the movement
6. User can adjust date range and compare different series

---

## Initial Data Priorities

### Time Series Sources
Prioritize these sources in this approximate order:
1. **FRED** for macroeconomic and rates series
2. **BLS** for labor market data
3. **U.S. Treasury** for Treasury yields / rates if needed directly
4. Other public economic sources only after the first pipeline works well

### Event Sources
Initial event retrieval can be simple and structured. Focus on events likely to matter for short-term rates:
- Fed announcements
- BLS employment releases
- CPI / inflation releases
- Treasury or macroeconomic releases
- major U.S. policy / economic news
- major market-moving headlines

At first, event ingestion can be semi-structured or rule-based rather than fully automated.

---

## Initial Analytical Use Case
The first end-to-end use case should answer:

**"How do recent noteworthy events relate to changes in U.S. short-term bond prices, with employment data as supporting context?"**

Example series candidates:
- 2-Year Treasury yield
- 3-Month Treasury yield
- 1-Year Treasury yield
- unemployment rate
- nonfarm payroll changes
- labor force participation rate

---

## Recommended Technical Approach

### Preferred Stack
- **Backend:** Python
- **Frontend:** JavaScript / TypeScript web app
- **Database:** SQL-based relational database
- **Local environment:** Python virtual environment
- **Version control:** Git
- **Hosting:** Fly.io using `flyctl`

### Suggested Frameworks
These are recommendations, not hard constraints:

#### Backend
- FastAPI for API development
- Pydantic for schemas and validation
- SQLAlchemy for ORM / database access
- Alembic for migrations
- httpx or requests for data ingestion
- pandas for lightweight data processing

#### Frontend
- React with Vite or Next.js
- TypeScript strongly preferred
- a charting library such as Recharts, ECharts, or Plotly
- lightweight component library optional

#### Database
- PostgreSQL preferred for production
- SQLite acceptable for very early local prototyping only

---

## Suggested Architecture
Organize the system into clear modules.

### Backend Domains
- `ingestion/`
  - fetch public time series
  - fetch or store event data
- `normalization/`
  - convert source data into consistent schema
- `analysis/`
  - align events with time series windows
  - compute simple change metrics
  - generate interpretive summaries
- `api/`
  - expose endpoints to frontend
- `db/`
  - models, migrations, repositories
- `jobs/`
  - scheduled refresh tasks

### Frontend Domains
- series selection UI
- comparison chart UI
- event timeline / annotations
- insight summary panel
- filter controls for date range and event categories

---

## Canonical Data Model (Initial)
Agents should aim toward a clean internal schema even if sources differ.

### `series`
Metadata for a time series
- `id`
- `source`
- `source_series_id`
- `name`
- `description`
- `units`
- `frequency`
- `category`
- `is_active`

### `observations`
Normalized time series observations
- `id`
- `series_id`
- `observation_date`
- `value`
- `created_at`

### `events`
Noteworthy events for annotation
- `id`
- `event_date`
- `title`
- `summary`
- `category`
- `source`
- `source_url`
- `importance_score`
- `created_at`

### `analysis_runs` (optional early, helpful later)
- `id`
- `series_a_id`
- `series_b_id`
- `date_range_start`
- `date_range_end`
- `summary_text`
- `created_at`

---

## Initial API Goals
Build simple, stable endpoints first.

### Example endpoints
- `GET /health`
- `GET /series`
- `GET /series/{id}/observations?start=...&end=...`
- `GET /events?start=...&end=...&category=...`
- `GET /compare?series_a=...&series_b=...&start=...&end=...`
- `GET /insights?series_a=...&series_b=...&start=...&end=...`

The compare endpoint should return:
- metadata for both series
- normalized observations
- relevant events in range
- simple summary statistics

The insights endpoint should return:
- plain-language explanation
- detected inflection windows
- nearest events around those windows
- confidence / caveat metadata if available

---

## Milestones

### Milestone 0: Project Setup
Goal: establish a clean development foundation

Tasks:
- initialize git repository
- define base directory structure
- create Python virtual environment workflow
- create backend service skeleton
- create frontend scaffold
- set up local database
- add linting / formatting / test tooling
- create `.env.example`
- create Fly.io deployment placeholders

Definition of done:
- project runs locally
- backend health endpoint works
- frontend loads
- repository is committed and reproducible

---

### Milestone 1: First Data Pipeline
Goal: pull and store at least one bond-related series and one labor-related series

Tasks:
- connect to FRED and/or BLS
- choose 2-4 initial series
- normalize observations into database
- create repeatable ingestion scripts
- document source mappings

Definition of done:
- data can be fetched reliably
- data is stored in normalized schema
- API can return observations for chosen series

---

### Milestone 2: Event Timeline
Goal: create a minimal, useful event layer

Tasks:
- define event schema
- ingest a small set of recent economic / policy events
- classify event categories
- expose events via API

Definition of done:
- events can be stored and retrieved by date range
- frontend can display event markers or event list near chart data

---

### Milestone 3: Comparison View
Goal: allow users to compare two series on one workflow

Tasks:
- build series selector UI
- load two time series together
- support a shared date range
- visualize comparison clearly
- display recent related events

Definition of done:
- user can compare two series end-to-end in browser
- chart and event timeline are both functional

---

### Milestone 4: Plain-Language Insights
Goal: provide basic analytical interpretation

Tasks:
- calculate simple changes over time
- detect large moves / inflection points
- associate nearby events with those moves
- generate short narrative summaries

Definition of done:
- user receives a readable summary of what changed and possible event context
- output is deterministic and auditable

---

### Milestone 5: Deployment
Goal: make the MVP accessible in a hosted environment

Tasks:
- configure Fly.io app
- set up environment variables
- configure production database
- deploy backend and frontend
- verify ingestion / refresh process in hosted environment

Definition of done:
- application is accessible online
- core compare workflow works in production

---

## Engineering Priorities
Agents should optimize for:
1. correctness of data ingestion
2. consistency of internal schemas
3. ease of debugging
4. modularity of source connectors
5. fast local iteration
6. simple deployment

Do not prematurely optimize for scale.

---

## Quality Standards
All code should aim to be:
- readable
- modular
- typed where practical
- tested at the service and API layer
- easy for future agents to extend

At minimum, add:
- unit tests for normalization logic
- integration tests for core API routes
- smoke tests for ingestion workflows where practical

---

## Development Conventions

### Python
- use virtual environment
- prefer clear module boundaries
- use type hints
- keep business logic out of route handlers
- separate source adapters from normalized domain logic

### SQL / DB
- use migrations
- avoid hidden schema drift
- keep core tables simple and explicit
- index by date where appropriate

### Frontend
- keep components small and composable
- separate API client logic from presentation
- make charts understandable for non-expert users
- avoid finance jargon unless clearly explained

---

## Repo Structure (Suggested)
```txt
everyday-analyst/
  backend/
    app/
      api/
      analysis/
      db/
      ingestion/
      models/
      schemas/
      services/
      main.py
    tests/
    pyproject.toml
    alembic/
  frontend/
    src/
      components/
      pages/
      lib/
      api/
  docs/
  scripts/
  .env.example
  AGENTS.md
  README.md
```
---

## Decision Rule for Agents
If a technical decision is unclear, prefer the option that:
- reduces implementation time
- improves determinism
- keeps the system auditable
- supports the initial narrow use case well