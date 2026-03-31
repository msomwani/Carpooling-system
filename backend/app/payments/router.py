import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.payments.service import PaymentService
from app.common.db import get_db
from app.bookings.models import Booking
from app.rides.models import Ride
from app.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

payment_service = PaymentService()


class CreateOrderRequest(BaseModel):
    amount: int       # Amount in INR (we convert to paise inside the service)
    booking_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_id: str # Added booking_id to link the payment


@router.post("/create-order")
async def create_order(body: CreateOrderRequest):
    """
    Creates a Razorpay order.
    Called by the frontend BEFORE showing the payment modal.
    Returns the order object (including order.id) needed to open the modal.
    """
    logger.info(f"Payment order request: amount={body.amount}, booking_id={body.booking_id}")
    order = payment_service.create_order(body.amount, body.booking_id)
    return order


@router.post("/verify")
async def verify_payment(body: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """
    Verifies the Razorpay payment signature after the user pays.
    Also creates an on-hold transfer to the driver using Razorpay Route.
    """
    # 1. Verify Signature
    is_valid = payment_service.verify_payment(
        body.razorpay_order_id,
        body.razorpay_payment_id,
        body.razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed. Invalid signature.")

    # 2. Fetch Booking and Ride details
    booking = db.query(Booking).filter(Booking.id == body.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found during verification")

    ride = db.query(Ride).filter(Ride.id == booking.ride_id).first()
    driver = db.query(User).filter(User.id == ride.driver_id).first()

    # 3. Create Transfer (On Hold) to Driver
    # In production, driver MUST have a linked razorpay_account_id.
    # We use a dummy for testing if none exists.
    account_id = driver.razorpay_account_id or "acc_test_dummy_123"
    
    amount_in_paise = int(booking.seats_booked * ride.price_per_seat * 100)
    
    try:
        transfer_response = payment_service.create_transfer(
            payment_id=body.razorpay_payment_id,
            account_id=account_id,
            amount_in_paise=amount_in_paise
        )
        # Razorpay returns a list of transfers
        transfer_id = transfer_response['items'][0]['id'] if 'items' in transfer_response else None
    except Exception as e:
        logger.error(f"Failed to create Razorpay transfer: {str(e)}")
        # We still mark it as paid so the user doesn't lose money, 
        # but the admin will need to settle it manually if the transfer failed.
        transfer_id = None

    # 4. Update Booking Status
    booking.status = "PAID_HELD"
    booking.razorpay_order_id = body.razorpay_order_id
    booking.razorpay_payment_id = body.razorpay_payment_id
    booking.razorpay_transfer_id = transfer_id
    
    db.commit()

    return {
        "status": "verified", 
        "booking_status": "PAID_HELD", 
        "payment_id": body.razorpay_payment_id,
        "transfer_id": transfer_id
    }
