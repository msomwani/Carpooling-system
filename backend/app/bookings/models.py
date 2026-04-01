import uuid
import enum

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.common.db import Base


class BookingTripStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    READY_AT_PICKUP = "READY_AT_PICKUP"
    BOARDED = "BOARDED"
    DROPPED = "DROPPED"
    NO_SHOW = "NO_SHOW"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id = Column(UUID(as_uuid=True), ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    seats_booked = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False) # PENDING_PAYMENT, PAID_HELD, CONFIRMED, REFUNDED, CANCELLED
    trip_status = Column(
        SAEnum(BookingTripStatus, name="bookingtripstatus"),
        nullable=False,
        default=BookingTripStatus.BOOKED,
        server_default=BookingTripStatus.BOOKED.value,
    )
    boarded_seats = Column(Integer, nullable=False, default=0, server_default="0")

    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_transfer_id = Column(String(100), nullable=True)
    passenger_ready_at = Column(DateTime(timezone=True), nullable=True)
    boarded_at = Column(DateTime(timezone=True), nullable=True)
    passenger_boarding_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    settled_amount_paise = Column(Integer, nullable=False, default=0, server_default="0")
    refunded_amount_paise = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
