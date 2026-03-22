from pydantic import BaseModel, ConfigDict, field_validator
import re
from uuid import UUID
from datetime import datetime
from typing import Literal

class VehicleCreateRequest(BaseModel):
    make: str
    model: str
    color: str
    license_plate: str
    type: Literal["CAR", "BIKE"]

    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        # Normalize: uppercase and remove non-alphanumeric
        normalized = re.sub(r'[^A-Z0-9]', '', v.upper())
        
        # Standard Indian format: 
        # State(2) District(2) Series(0-2) Number(4)
        # e.g. GJ06BS4147
        pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{0,2}[0-9]{4}$'
        if not re.match(pattern, normalized):
            raise ValueError("Invalid Indian license plate format (e.g., GJ06BS4147)")
        
        return normalized

class VehicleResponse(BaseModel):
    id: UUID
    owner_id: UUID
    make: str
    model: str
    color: str
    license_plate: str
    type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
