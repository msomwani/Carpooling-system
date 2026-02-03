from pydantic import BaseModel, Field
from uuid import UUID


class BookingCreateRequest(BaseModel):
    ride_id: UUID
    seats: int = Field(gt=0)


class BookingResponse(BaseModel):
    booking_id: UUID
    status: str
