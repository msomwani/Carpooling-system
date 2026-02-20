import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.common.db import SessionLocal
from app.bookings.service import BookingService
from app.bookings.schemas import BookingCreateRequest, BookingResponse, BookingHistoryResponse
from app.auth.dependencies import get_current_user_id
from app.bookings.cancel_service import CancellationService
from app.bookings.history_model import BookingHistory

logger = logging.getLogger(__name__)

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
