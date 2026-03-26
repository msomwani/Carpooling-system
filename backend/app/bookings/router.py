import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.bookings.service import BookingService
from app.bookings.schemas import (
    BookingCreateRequest, 
    BookingResponse, 
    BookingHistoryResponse,
    MyBookingResponse
)
from app.auth.dependencies import get_current_user_id
from app.bookings.cancel_service import CancellationService
from app.bookings.history_model import BookingHistory
from app.rides.models import Ride
from app.rides.service import RideService

from app.bookings.models import Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/my", response_model=list[MyBookingResponse])
def get_my_bookings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Fetch current user's active bookings with ride details."""
    results = (
        db.query(Booking, Ride)
        .join(Ride, Booking.ride_id == Ride.id)
        .filter(Booking.passenger_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    
    # Sync ride status for all active rides in the results
    for _, ride in results:
        RideService.sync_ride_status(db, ride)

    return [
        MyBookingResponse(
            booking_id=booking.id,
            ride_id=ride.id,
            source=ride.source,
            destination=ride.destination,
            departure_time=ride.departure_time,
            seats_booked=booking.seats_booked,
            price_per_seat=ride.price_per_seat,
            status=booking.status,
            created_at=booking.created_at,
        )
        for booking, ride in results
    ]





@router.post("", response_model=BookingResponse)
def create_booking(
    payload: BookingCreateRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id

    logger.info(
        "Booking request received",
        extra={"correlation_id": correlation_id},
    )

    try:
        booking = BookingService.create_booking(
            db=db,
            ride_id=payload.ride_id,
            passenger_id=user_id,
            seats_requested=payload.seats,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

        logger.info(
            "Booking created successfully",
            extra={"correlation_id": correlation_id},
        )

        return BookingResponse(
            booking_id=booking.id,
            status=booking.status,
        )

    except ValueError as e:
        logger.error(
            "Booking failed",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(status_code=400, detail=f"booking failed: {str(e)}")


@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id

    logger.info(
        "Cancellation request received",
        extra={"correlation_id": correlation_id},
    )

    try:
        booking = CancellationService.cancel_booking(
            db=db,
            booking_id=booking_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        logger.info(
            "Booking cancelled successfully",
            extra={"correlation_id": correlation_id},
        )

        return {"status": "cancelled", "booking_id": booking.id}

    except ValueError as e:
        logger.error(
            "Cancellation failed",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=list[BookingHistoryResponse])
def get_booking_history(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(BookingHistory)
        .filter(BookingHistory.user_id == user_id)
        .order_by(BookingHistory.occurred_at.desc())
        .limit(limit)
        .all()
    )
    return [
        BookingHistoryResponse(
            event_id=row.event_id,
            booking_id=row.booking_id,
            ride_id=row.ride_id,
            action=row.action,
            occurred_at=row.occurred_at,
            correlation_id=row.correlation_id,
        )
        for row in rows
    ]

@router.get("/status/{ride_id}")
def get_booking_status(
    ride_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Check if the current user has a confirmed booking for this ride."""
    booking = (
        db.query(Booking)
        .filter(Booking.ride_id == ride_id, Booking.passenger_id == user_id, Booking.status == "CONFIRMED")
        .first()
    )
    if booking:
        return {"has_booking": True, "booking_id": str(booking.id), "status": booking.status}
    return {"has_booking": False, "booking_id": None, "status": None}
