from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class RideCreateRequest(BaseModel):
    source: str = Field(..., min_length=2, max_length=200)
    source_lat: float | None = Field(default=None, ge=-90, le=90)
    source_lng: float | None = Field(default=None, ge=-180, le=180)

    destination: str = Field(..., min_length=2, max_length=200)
    destination_lat: float | None = Field(default=None, ge=-90, le=90)
    destination_lng: float | None = Field(default=None, ge=-180, le=180)

    departure_time: datetime
    total_seats: int = Field(gt=0, le=8)  # No ride should have more than 8 seats
    price_per_seat: int = Field(ge=0, le=10000)  # Reasonable max price cap
    vehicle_id: UUID
    route_geometry: str | None = Field(default=None, max_length=100000)  # WKT or GeoJSON string

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
    price_per_seat: int
    status: Literal["ACTIVE", "COMPLETED", "CANCELLED"] = "ACTIVE"
    vehicle_id: UUID | None = None
    route_geometry: str | None = None

    @field_validator("route_geometry", mode="before")
    @classmethod
    def convert_geometry(cls, v):
        if v is None:
            return v
            
        # If it's already a WKT string (which we now enforce in the Service layer), return as is
        if isinstance(v, str) and (v.startswith("LINESTRING") or v.startswith("POINT")):
            return v
            
        # Fallback for hex WKB (if ST_AsText wasn't used)
        if isinstance(v, str):
            # We don't need shapely here if we trust the Service layer uses ST_AsText.
            # However, we'll keep it safe by returning what we have.
            return v
                
        # Handle GeoAlchemy2 WKBElement by returning its string representation (usually Hex)
        # The Service layer should use ST_AsText to avoid this fallback.
        try:
            return str(v)
        except Exception:
            return None


class RideDetailResponse(BaseModel):
    ride: RideResponse
    driver_name: str
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_color: str | None = None
    vehicle_license_plate: str | None = None
