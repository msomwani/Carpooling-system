from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field, model_validator, ConfigDict


class RideCreateRequest(BaseModel):
    source: str
    source_lat: float | None = Field(default=None, ge=-90, le=90)
    source_lng: float | None = Field(default=None, ge=-180, le=180)

    destination: str
    destination_lat: float | None = Field(default=None, ge=-90, le=90)
    destination_lng: float | None = Field(default=None, ge=-180, le=180)

    departure_time: datetime
    total_seats: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_coordinate_pairs(self):
        if (self.source_lat is None) != (self.source_lng is None):
            raise ValueError("Both source_lat and source_lng must be provided together")
        if (self.destination_lat is None) != (self.destination_lng is None):
            raise ValueError("Both destination_lat and destination_lng must be provided together")
        return self


class RideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    driver_id: UUID
    source: str
    source_lat: float | None = None
    source_lng: float | None = None

    destination: str
    destination_lat: float | None = None
    destination_lng: float | None = None

    departure_time: datetime
    total_seats: int
    available_seats: int
    status: Literal["ACTIVE", "COMPLETED", "CANCELLED"] = "ACTIVE"
