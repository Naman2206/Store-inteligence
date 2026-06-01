"""
Store Intelligence API — Brigade Road, Bangalore
April 2026 | UpGrad Placement Challenge
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import metrics, funnel, anomalies, events, health
from api.data_loader import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading sales data...")
    app.state.loader = DataLoader()
    app.state.loader.load()
    logger.info(f"Loaded {len(app.state.loader.df)} transaction rows")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Store Intelligence API",
    description="Real-time store analytics for Brigade Road Bangalore",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(funnel.router, prefix="/funnel", tags=["funnel"])
app.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
app.include_router(events.router, prefix="/events", tags=["events"])
