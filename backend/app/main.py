from fastapi import FastAPI
from app.common.logging_config import setup_logging
from app.common.middleware import correlation_middleware

from app.auth.router import router as auth_router
from app.rides.router import router as rides_router
from app.bookings.router import router as booking_router

setup_logging()

app = FastAPI()
app.middleware("http")(correlation_middleware)

app.include_router(auth_router)
app.include_router(booking_router)
app.include_router(rides_router)
