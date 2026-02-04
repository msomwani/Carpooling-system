from fastapi import FastAPI
from app.bookings.router import router as booking_router
from app.auth.router import router as auth_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(booking_router)
