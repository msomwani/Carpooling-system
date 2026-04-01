from uuid import uuid4

from app.auth.dependencies import get_current_user_id
from app.bookings.models import Booking
from app.main import app


def test_get_booking_status_paid_held(client, db, sample_passenger, sample_ride):
    booking = Booking(
        id=uuid4(),
        ride_id=sample_ride.id,
        passenger_id=sample_passenger.id,
        seats_booked=1,
        status="PAID_HELD",
    )
    db.add(booking)
    db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)

    response = client.get(f"/bookings/status/{sample_ride.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["has_booking"] is True
    assert data["booking_id"] == str(booking.id)
    assert data["status"] == "PAID_HELD"
    assert data["trip_status"] == "BOOKED"
    assert data["boarded_seats"] == 0
    assert data["can_cancel"] is True

    app.dependency_overrides.clear()


def test_get_booking_status_none(client, sample_passenger, sample_ride):
    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)

    response = client.get(f"/bookings/status/{sample_ride.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["has_booking"] is False
    assert data["booking_id"] is None
    assert data["status"] is None
    assert data["trip_status"] is None

    app.dependency_overrides.clear()
