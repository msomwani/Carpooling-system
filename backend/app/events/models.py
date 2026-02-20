from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.common.db import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True)
    consumer_name = Column(String(100), primary_key=True)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
