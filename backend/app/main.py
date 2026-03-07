from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.common.logging_config import setup_logging
from app.common.middleware import correlation_middleware
from app.common.db import SessionLocal
from app.common.redis import redis_client
from app.common.kafka import producer
from app.common.metrics import get_metrics

from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.rides.router import router as rides_router
from app.bookings.router import router as booking_router
from app.analytics.router import router as analytics_router
from app.maps.router import router as maps_router
from app.config.settings import settings

setup_logging()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
app.middleware("http")(correlation_middleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(booking_router)
app.include_router(rides_router)
app.include_router(analytics_router)
app.include_router(maps_router)

# Serve static frontend files (maps.html, etc.)
_static_dir = Path(__file__).resolve().parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

@app.get("/healthz")
def health_check():
    return {"status": "ok"}


@app.get("/readyz")
def readiness_check():
    # DB check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        return {"status": "not_ready", "component": "database"}

    # Redis check
    try:
        redis_client.ping()
    except Exception:
        return {"status": "not_ready", "component": "redis"}

    # Kafka check
    try:
        producer.list_topics(timeout=2)
    except Exception:
        return {"status": "not_ready", "component": "kafka"}

    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return get_metrics()
