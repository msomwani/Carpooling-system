import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.bookings.models import Booking
from app.common.db import get_db
from app.outbox.models import OutboxEvent
from app.payments.service import PaymentService
from app.rides.models import Ride

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

payment_service = PaymentService()


class CreateOrderRequest(BaseModel):
    booking_id: str
    amount: int | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_id: str # Added booking_id to link the payment


@router.post("/create-order")
async def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Creates a Razorpay order.
    Called by the frontend BEFORE showing the payment modal.
    Returns the order object (including order.id) needed to open the modal.
    """
    booking = (
        db.query(Booking)
        .filter(Booking.id == body.booking_id, Booking.passenger_id == user_id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "PENDING_PAYMENT":
        raise HTTPException(status_code=400, detail="Booking is not awaiting payment.")

    ride = db.query(Ride).filter(Ride.id == booking.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found during order creation")

    expected_amount = booking.seats_booked * ride.price_per_seat
    if expected_amount <= 0:
        raise HTTPException(status_code=400, detail="This booking does not require online payment.")

    logger.info(f"Payment order request: booking_id={body.booking_id}, amount={expected_amount}")
    order = payment_service.create_order(expected_amount, body.booking_id)
    booking.razorpay_order_id = order.get("id")
    db.commit()
    return order


@router.post("/verify")
async def verify_payment(
    body: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Verifies the Razorpay payment signature after the user pays and keeps funds on hold
    until the ride is completed.
    """
    is_valid = payment_service.verify_payment(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed. Invalid signature.")

    # 2. Fetch Booking and Ride details
    booking = (
        db.query(Booking)
        .filter(Booking.id == body.booking_id, Booking.passenger_id == user_id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found during verification")
    if booking.status == "PAID_HELD":
        if (
            booking.razorpay_order_id == body.razorpay_order_id
            and booking.razorpay_payment_id == body.razorpay_payment_id
        ):
            return {
                "status": "verified",
                "booking_status": "PAID_HELD",
                "payment_id": body.razorpay_payment_id,
                "transfer_id": booking.razorpay_transfer_id,
            }
        raise HTTPException(status_code=400, detail="Payment has already been verified for this booking.")
    if booking.status != "PENDING_PAYMENT":
        raise HTTPException(status_code=400, detail="Booking is not awaiting payment verification.")
    if not booking.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment has not been initialized for this booking.")
    if booking.razorpay_order_id != body.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Payment order does not match this booking.")

    ride = db.query(Ride).filter(Ride.id == booking.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found during verification")

    booking.status = "PAID_HELD"
    booking.razorpay_order_id = body.razorpay_order_id
    booking.razorpay_payment_id = body.razorpay_payment_id
    booking.razorpay_transfer_id = None

    db.add(
        OutboxEvent(
            event_type="booking.confirmed",
            payload={
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "payment_status": booking.status,
                "trip_status": booking.trip_status.value,
            },
        )
    )
    db.commit()

    return {
        "status": "verified",
        "booking_status": "PAID_HELD",
        "payment_id": body.razorpay_payment_id,
        "transfer_id": None,
    }
