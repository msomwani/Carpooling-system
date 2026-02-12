from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.common.db import SessionLocal
from app.bookings.service import BookingService
from app.bookings.schemas import BookingCreateRequest, BookingResponse
from app.auth.dependencies import get_current_user_id
from app.bookings.cancel_service import CancellationService


router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=BookingResponse)
def create_booking(
    payload: BookingCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        booking = BookingService.create_booking(
            db=db,
            ride_id=payload.ride_id,
            passenger_id=user_id, 
            seats_requested=payload.seats,
            idempotency_key=idempotency_key
        )
        return BookingResponse(
            booking_id=booking.id,
            status=booking.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"booking failed :{str(e)}")


@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        booking = CancellationService.cancel_booking(
            db=db,
            booking_id=booking_id,
            user_id=user_id,
        )
        return {"status": "cancelled", "booking_id": booking.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
