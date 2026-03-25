import uuid
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from geoalchemy2 import Geography
import enum

from app.common.db import Base


class RideStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Ride(Base):
    __tablename__ = "rides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)

    source = Column(String(255), nullable=False)
    source_lat = Column(Float, nullable=True)
    source_lng = Column(Float, nullable=True)
    source_location = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)

    destination = Column(String(255), nullable=False)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)
    destination_location = Column(Geography(geometry_type='POINT', srid=4326), nullable=True)
    route_geometry = Column(Geography(geometry_type='LINESTRING', srid=4326), nullable=True)
    departure_time = Column(DateTime(timezone=True), nullable=False)

    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)

    status = Column(
        SAEnum(RideStatus, name="ridestatus"),
        nullable=False,
        default=RideStatus.ACTIVE,
        server_default=RideStatus.ACTIVE.value,
    )
    price_per_seat = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
