import uuid
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.common.db import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("ride_id", "passenger_id", name="unique_ride_passenger"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id = Column(UUID(as_uuid=True), ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    seats_booked = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
