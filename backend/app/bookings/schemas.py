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
