import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.common.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=True)  # nullable for Google OAuth users
    role = Column(String(20), nullable=False)

    phone_number = Column(String(20), nullable=True)
    phone_verified = Column(Boolean, nullable=False, default=False)

    # Email verification
    is_email_verified = Column(Boolean, nullable=False, default=False)

    # Razorpay Route integration
    razorpay_account_id = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
