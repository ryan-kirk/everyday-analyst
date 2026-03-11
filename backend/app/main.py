from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.compare import router as compare_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.series import router as series_router
from app.db.base import Base
from app.db.database import engine
from app import models  # noqa: F401  # Ensures model metadata is registered.


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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
