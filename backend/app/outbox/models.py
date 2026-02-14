import uuid
from sqlalchemy import Column,String,DateTime,Boolean
from sqlalchemy.dialects.postgresql import UUID,JSONB
from sqlalchemy.sql import func

from app.common.db import Base

class OutboxEvent(Base):
    __tablename__="outbox_events"

    id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    event_type=Column(String(100),nullable=False)
    payload=Column(JSONB,nullable=False)
    processed=Column(Boolean,default=False,nullable=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())