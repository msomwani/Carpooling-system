import pytest
from uuid import uuid4
from app.main import app
from app.bookings.models import Booking
from app.auth.dependencies import get_current_user_id

def test_get_booking_status_confirmed(client, db, sample_passenger, sample_ride):
    """Issue 7: Verify /bookings/status returns consistent schema for confirmed booking."""
    # 1. Create a confirmed booking
    booking = Booking(
        id=uuid4(),
        ride_id=sample_ride.id,
        passenger_id=sample_passenger.id,
        seats_booked=1,
        status="CONFIRMED"
    )
    db.add(booking)
    db.commit()
    
    # 2. Mock auth as the passenger
    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)
    
    # 3. Act: Check status
    response = client.get(f"/bookings/status/{sample_ride.id}")
    
    # 4. Assert: Correct schema and values
    assert response.status_code == 200
    data = response.json()
    assert data["has_booking"] is True
    assert data["booking_id"] == str(booking.id)
    assert data["status"] == "CONFIRMED"
    
    app.dependency_overrides.clear()

def test_get_booking_status_none(client, sample_passenger, sample_ride):
    """Issue 7: Verify /bookings/status returns consistent schema when no booking exists."""
    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)
    
    response = client.get(f"/bookings/status/{sample_ride.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["has_booking"] is False
    assert data["booking_id"] is None
    assert data["status"] is None
    
    app.dependency_overrides.clear()
