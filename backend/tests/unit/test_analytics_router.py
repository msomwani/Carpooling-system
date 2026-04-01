from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.dependencies import get_current_user_id
from app.bookings.models import Booking
from app.main import app
from app.rides.models import Ride


def test_get_my_analytics_requires_authentication(client):
    response = client.get("/analytics/me?role=passenger")

    assert response.status_code == 401


def test_get_my_analytics_for_passenger(client, db, sample_driver, sample_passenger):
    ride_one = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Anand",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=2),
        total_seats=4,
        available_seats=3,
        price_per_seat=120,
    )
    ride_two = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Surat",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=4),
        total_seats=4,
        available_seats=2,
        price_per_seat=200,
    )
    ride_three = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Ahmedabad",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=6),
        total_seats=4,
        available_seats=3,
        price_per_seat=300,
    )
    db.add_all([ride_one, ride_two, ride_three])
    db.commit()

    db.add_all([
        Booking(
            id=uuid4(),
            ride_id=ride_one.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="CONFIRMED",
        ),
        Booking(
            id=uuid4(),
            ride_id=ride_two.id,
            passenger_id=sample_passenger.id,
            seats_booked=2,
            status="PAID_HELD",
        ),
        Booking(
            id=uuid4(),
            ride_id=ride_three.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="CANCELLED",
        ),
    ])
    db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)

    response = client.get("/analytics/me?role=passenger")

    assert response.status_code == 200
    assert response.json() == {
        "role": "passenger",
        "window": "lifetime",
        "stats": {
            "total_bookings": 2,
            "cancelled_bookings": 1,
            "seats_booked": 3,
            "total_spend_inr": 520,
        },
    }

    app.dependency_overrides.clear()


def test_get_my_analytics_for_driver_syncs_completed_rides(client, db, sample_driver, sample_passenger):
    past_ride = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Halol",
        departure_time=datetime.now(timezone.utc) - timedelta(hours=3),
        total_seats=4,
        available_seats=2,
        price_per_seat=150,
        status="ACTIVE",
    )
    future_ride = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Bharuch",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
        total_seats=4,
        available_seats=3,
        price_per_seat=220,
        status="ACTIVE",
    )
    db.add_all([past_ride, future_ride])
    db.commit()

    db.add_all([
        Booking(
            id=uuid4(),
            ride_id=past_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=2,
            status="CONFIRMED",
        ),
        Booking(
            id=uuid4(),
            ride_id=future_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="PAID_HELD",
        ),
        Booking(
            id=uuid4(),
            ride_id=future_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="CANCELLED",
        ),
    ])
    db.commit()

    app.dependency_overrides[get_current_user_id] = lambda: str(sample_driver.id)

    response = client.get("/analytics/me?role=driver")

    assert response.status_code == 200
    assert response.json() == {
        "role": "driver",
        "window": "lifetime",
        "stats": {
            "rides_created": 2,
            "rides_completed": 1,
            "seats_shared": 3,
            "gross_earnings_inr": 520,
        },
    }

    db.refresh(past_ride)
    assert past_ride.status.value == "COMPLETED"

    app.dependency_overrides.clear()
