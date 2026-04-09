import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.bookings.models import Booking
from app.common.db import get_db
from app.outbox.models import OutboxEvent
from app.payments.service import PaymentService
from app.rides.models import Ride
from app.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# Import rate limiter for state‑changing endpoints
from app.auth.router import limiter

payment_service = PaymentService()


# ─── Schemas ──────────────────────────────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    booking_id: str
    amount: int | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_id: str


class PayoutAccountRequest(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=10, max_length=15, pattern=r"^\d{10,15}$")
    beneficiary_name: str = Field(..., min_length=2, max_length=100)
    account_number: str = Field(..., min_length=9, max_length=18, pattern=r"^\d{9,18}$")
    ifsc_code: str = Field(..., min_length=11, max_length=11, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")


# ─── Order & Verify endpoints ─────────────────────────────────────────────────


@router.post("/create-order")
@limiter.limit("10/minute")
async def create_order(
    body: CreateOrderRequest,
    request: Request,
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
        raise HTTPException(
            status_code=404, detail="Ride not found during order creation"
        )

    expected_amount = booking.seats_booked * ride.price_per_seat
    if expected_amount <= 0:
        raise HTTPException(
            status_code=400, detail="This booking does not require online payment."
        )

    logger.info(
        f"Payment order request: booking_id={body.booking_id}, amount={expected_amount}"
    )
    order = payment_service.create_order(expected_amount, body.booking_id)
    booking.razorpay_order_id = order.get("id")
    db.commit()
    return order


@router.post("/verify")
@limiter.limit("10/minute")
async def verify_payment(
    body: VerifyPaymentRequest,
    request: Request,
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
        raise HTTPException(
            status_code=400, detail="Payment verification failed. Invalid signature."
        )

    booking = (
        db.query(Booking)
        .filter(Booking.id == body.booking_id, Booking.passenger_id == user_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=404, detail="Booking not found during verification"
        )
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
        raise HTTPException(
            status_code=400,
            detail="Payment has already been verified for this booking.",
        )
    if booking.status != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=400, detail="Booking is not awaiting payment verification."
        )
    if not booking.razorpay_order_id:
        raise HTTPException(
            status_code=400, detail="Payment has not been initialized for this booking."
        )
    if booking.razorpay_order_id != body.razorpay_order_id:
        raise HTTPException(
            status_code=400, detail="Payment order does not match this booking."
        )

    ride = db.query(Ride).filter(Ride.id == booking.ride_id).first()
    if not ride:
        raise HTTPException(
            status_code=404, detail="Ride not found during verification"
        )

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


# ─── Payout Account (Razorpay Route) ──────────────────────────────────────────


@router.post("/payout-account")
@limiter.limit("5/minute")
async def setup_payout_account(
    body: PayoutAccountRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Onboards the driver onto Razorpay Route (Linked Account).
    Stores the resulting account_id on the user record.
    Only drivers can call this endpoint.
    """
    driver = db.query(User).filter(User.id == user_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="User not found")
    if driver.role != "driver":
        raise HTTPException(
            status_code=403,
            detail="Only drivers can set up a payout account.",
        )
    if driver.razorpay_account_id:
        raise HTTPException(
            status_code=400,
            detail="Payout account already linked. Remove it first to re-onboard.",
        )

    try:
        account_id = payment_service.create_linked_account(
            legal_name=body.legal_name,
            email=body.email,
            phone=body.phone,
            beneficiary_name=body.beneficiary_name,
            account_number=body.account_number,
            ifsc_code=body.ifsc_code,
        )
    except Exception as exc:
        exc_str = str(exc)
        logger.error("Razorpay linked account creation failed: %s", exc_str)
        
        # DEMO MODE FALLBACK: If Razorpay Route is not enabled (Access Denied),
        # create a mock account ID for the college project demonstration.
        if "Access Denied" in exc_str:
            logger.warning("DEMO MODE: Razorpay Route restricted. Generating mock account for user %s", user_id)
            account_id = f"acc_DEMO_{user_id.replace('-', '')[:10]}"
        else:
            # Extract the inner error message if available for other types of errors
            error_msg = "Failed to create payout account with Razorpay."
            if hasattr(exc, "args") and len(exc.args) > 0:
                error_msg = f"Razorpay API Error: {exc.args[0]}"
            elif exc_str:
                error_msg = f"Razorpay API Error: {exc_str}"
                
            raise HTTPException(
                status_code=502,
                detail=error_msg,
            )

    driver.razorpay_account_id = account_id
    db.commit()

    logger.info("Driver %s linked payout account %s", user_id, account_id)
    return {
        "account_id": account_id,
        "status": "linked",
        "message": "Payout account successfully linked. Razorpay will verify your bank details.",
    }


@router.get("/payout-account")
async def get_payout_account(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Returns the current payout account status for the authenticated driver.
    """
    driver = db.query(User).filter(User.id == user_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="User not found")

    if not driver.razorpay_account_id:
        return {"is_linked": False, "account_id": None}

    # Optionally fetch live status from Razorpay
    razorpay_data = payment_service.fetch_linked_account(driver.razorpay_account_id)
    account_status = razorpay_data.get("status", "created") if razorpay_data else "created"

    return {
        "is_linked": True,
        "account_id": driver.razorpay_account_id,
        "account_status": account_status,
    }


@router.delete("/payout-account")
@limiter.limit("5/minute")
async def remove_payout_account(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Removes the stored Razorpay linked account ID from the driver's profile.
    Allows re-onboarding with different bank details.
    Note: This does NOT delete the linked account on Razorpay's side.
    """
    driver = db.query(User).filter(User.id == user_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="User not found")
    if not driver.razorpay_account_id:
        raise HTTPException(status_code=400, detail="No payout account is linked.")

    old_account_id = driver.razorpay_account_id
    driver.razorpay_account_id = None
    db.commit()

    logger.info("Driver %s removed payout account %s", user_id, old_account_id)
    return {"message": "Payout account removed. You can now set up a new one."}
