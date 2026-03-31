import uuid
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.common.db import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id = Column(UUID(as_uuid=True), ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    seats_booked = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False) # PENDING_PAYMENT, PAID_HELD, CONFIRMED, CANCELLED

    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_transfer_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())