from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from sqlalchemy import text

from app.common.logging_config import setup_logging
from app.common.middleware import correlation_middleware
from app.common.db import SessionLocal
from app.common.redis import redis_client
from app.common.kafka import producer
from app.common.metrics import get_metrics

from app.users.router import router as users_router
from app.rides.router import router as rides_router
from app.bookings.router import router as booking_router
from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.vehicles.router import router as vehicles_router
from app.payments.router import router as payments_router
from app.config.settings import settings
from app.auth.router import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

setup_logging()

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security-hardening HTTP response headers on every response."""

    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Block embedding in iframes (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Force HTTPS in production
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy
        csp_blocks = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://accounts.google.com https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src * data: blob:",  # Allow images from anywhere (maps, avatars)
            "connect-src 'self' https://accounts.google.com",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_blocks)

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)
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
app.include_router(vehicles_router)
app.include_router(payments_router)
# Include notifications router for WebSocket endpoint
from app.notifications.router import router as notifications_router

app.include_router(notifications_router)

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
def metrics(request: Request):
    """Protected metrics endpoint — requires X-Metrics-Key header matching METRICS_API_KEY env var."""
    if (
        not settings.metrics_api_key
        or request.headers.get("X-Metrics-Key") != settings.metrics_api_key
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_metrics()


# Generic exception handler to avoid leaking internal details
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    import logging

    logging.error(f"Unhandled exception: {exc}", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
