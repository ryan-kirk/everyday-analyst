from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.compare import router as compare_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.insights import router as insights_router
from app.api.presets import router as presets_router
from app.api.series import router as series_router
from app.db.base import Base
from app.db.database import engine
from app.db.schema_utils import ensure_event_columns
from app import models  # noqa: F401  # Ensures model metadata is registered.

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_event_columns(engine)
    yield


app = FastAPI(
    title="Everyday Analyst API",
    description="Decision-support backend for comparing economic time series with event context.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(series_router)
app.include_router(events_router)
app.include_router(compare_router)
app.include_router(insights_router)
app.include_router(presets_router)

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
