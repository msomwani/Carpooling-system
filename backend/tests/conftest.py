import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from uuid import uuid4

from app.common.db import Base
from app.main import app
from app.users.models import User
from app.rides.models import Ride
from app.bookings.models import Booking
from app.bookings.history_model import BookingHistory
from app.bookings.idempotency_model import BookingIdempotency
from app.events.models import ProcessedEvent
from app.notifications.models import NotificationAttempt
from app.outbox.models import OutboxEvent
from app.config.settings import settings

# Test database URL - make sure this database exists
# Priority:
# 1) TEST_DATABASE_URL env var (optional override)
# 2) DATABASE_URL from .env via app settings
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.database_url)

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    This ensures tests are isolated and don't interfere with each other.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create a new session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client for API endpoint testing.
    Override the database dependency to use test database.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    from app.common.db import SessionLocal
    app.dependency_overrides[SessionLocal] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_driver(db):
    """Create a sample driver user for testing."""
    driver = User(
        id=uuid4(),
        name="Test Driver",
        email=f"driver_{uuid4()}@test.com",
        password_hash="hashed_password",
        role="driver",
        phone_number="1234567890",
        phone_verified=True
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@pytest.fixture
def sample_passenger(db):
    """Create a sample passenger user for testing."""
    passenger = User(
        id=uuid4(),
        name="Test Passenger",
        email=f"passenger_{uuid4()}@test.com",
        password_hash="hashed_password",
        role="passenger",
        phone_number="0987654321",
        phone_verified=True
    )
    db.add(passenger)
    db.commit()
    db.refresh(passenger)
    return passenger


@pytest.fixture
def sample_ride(db, sample_driver):
    """Create a sample ride for testing."""
    from datetime import datetime, timedelta
    
    ride = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Test Source",
        destination="Test Destination",
        departure_time=datetime.now() + timedelta(hours=2),
        total_seats=4,
        available_seats=4
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


@pytest.fixture
def multiple_passengers(db):
    """Create multiple passengers for concurrency testing."""
    passengers = []
    for i in range(10):
        passenger = User(
            id=uuid4(),
            name=f"Passenger {i}",
            email=f"passenger_{i}_{uuid4()}@test.com",
            password_hash="hashed_password",
            role="passenger"
        )
        db.add(passenger)
        passengers.append(passenger)
    
    db.commit()
    for p in passengers:
        db.refresh(p)
    
    return passengers
