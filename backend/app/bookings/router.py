import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.bookings.service import BookingService
from app.bookings.schemas import (
    BookingBoardRequest,
    BookingCreateRequest,
    BookingResponse,
    BookingHistoryResponse,
    MyBookingResponse,
    BookingStatusResponse,
)
from app.auth.dependencies import get_current_user_id
from app.bookings.cancel_service import CancellationService
from app.bookings.history_model import BookingHistory
from app.rides.models import Ride
from app.rides.service import RideService

from app.bookings.models import Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["Bookings"])

# Import rate limiter for state‑changing endpoints
from app.auth.router import limiter


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

    for booking, ride in results:
        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(booking)
        db.refresh(ride)

    return [
        MyBookingResponse(
            booking_id=booking.id,
            ride_id=ride.id,
            source=ride.source,
            destination=ride.destination,
            departure_time=ride.departure_time,
            seats_booked=booking.seats_booked,
            boarded_seats=booking.boarded_seats,
            price_per_seat=ride.price_per_seat,
            status=booking.status,
            trip_status=booking.trip_status.value,
            ride_status=ride.status.value,
            passenger_ready_at=booking.passenger_ready_at,
            passenger_boarding_confirmed_at=booking.passenger_boarding_confirmed_at,
            created_at=booking.created_at,
        )
        for booking, ride in results
    ]


@router.post("", response_model=BookingResponse)
@limiter.limit("10/minute")
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


@router.post("/{booking_id}/ready", response_model=BookingResponse)
@limiter.limit("10/minute")
def mark_ready_for_pickup(
    booking_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id
    try:
        booking = BookingService.mark_ready(
            db=db,
            booking_id=booking_id,
            passenger_id=user_id,
            correlation_id=correlation_id,
        )
        return BookingResponse(booking_id=booking.id, status=booking.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{booking_id}/board", response_model=BookingResponse)
@limiter.limit("10/minute")
def board_booking(
    booking_id: str,
    payload: BookingBoardRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id
    try:
        booking = BookingService.board_booking(
            db=db,
            booking_id=booking_id,
            driver_id=user_id,
            boarded_seats=payload.boarded_seats,
            correlation_id=correlation_id,
        )
        return BookingResponse(booking_id=booking.id, status=booking.status)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{booking_id}/confirm-boarding", response_model=BookingResponse)
@limiter.limit("10/minute")
def confirm_boarding(
    booking_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    correlation_id = request.state.correlation_id
    try:
        booking = BookingService.confirm_boarding(
            db=db,
            booking_id=booking_id,
            passenger_id=user_id,
            correlation_id=correlation_id,
        )
        return BookingResponse(booking_id=booking.id, status=booking.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{booking_id}/cancel")
@limiter.limit("10/minute")
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


@router.get("/status/{ride_id}", response_model=BookingStatusResponse)
def get_booking_status(
    ride_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    status_payload = BookingService.get_booking_status(
        db, ride_id=ride_id, passenger_id=user_id
    )
    return BookingStatusResponse(**status_payload)
