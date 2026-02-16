from fastapi import FastAPI
from sqlalchemy import text

from app.common.logging_config import setup_logging
from app.common.middleware import correlation_middleware
from app.common.db import SessionLocal
from app.common.redis import redis_client
from app.common.kafka import producer
from app.common.metrics import get_metrics

from app.auth.router import router as auth_router
from app.rides.router import router as rides_router
from app.bookings.router import router as booking_router

setup_logging()

app = FastAPI()
app.middleware("http")(correlation_middleware)

app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(rides_router)

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
