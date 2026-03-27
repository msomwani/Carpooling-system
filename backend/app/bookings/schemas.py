from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class BookingCreateRequest(BaseModel):
    ride_id: UUID
    seats: int = Field(gt=0)


class BookingResponse(BaseModel):
    booking_id: UUID
    status: str


class BookingHistoryResponse(BaseModel):
    event_id: UUID
    booking_id: UUID
    ride_id: UUID
    action: str
    occurred_at: datetime
    correlation_id: str | None = None


class MyBookingResponse(BaseModel):
    booking_id: UUID
    ride_id: UUID
    source: str
    destination: str
    departure_time: datetime
    seats_booked: int
    price_per_seat: int
    status: str
    created_at: datetime

class BookingStatusResponse(BaseModel):
    has_booking: bool
    booking_id: UUID | None = None
    status: str | None = None
