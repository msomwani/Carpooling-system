import uuid
from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.common.db import Base


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    error = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

