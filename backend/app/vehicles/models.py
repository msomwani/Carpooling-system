import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.common.db import Base


class VehicleType(str, enum.Enum):
    CAR = "CAR"
    BIKE = "BIKE"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    color = Column(String(50), nullable=False)
    license_plate = Column(String(20), nullable=False, unique=True)
    
    type = Column(
        SAEnum(VehicleType, name="vehicletype"),
        nullable=False,
        default=VehicleType.CAR,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
