from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class RideCreateRequest(BaseModel):
    source: str
    destination: str
    departure_time: datetime
    total_seats: int = Field(gt=0)


class RideResponse(BaseModel):
    id: UUID
    source: str
    destination: str
    departure_time: datetime
    available_seats: int
