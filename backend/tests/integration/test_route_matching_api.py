"""
Integration tests for the /rides/nearby API with Advanced Route Matching.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.rides.models import Ride, RideStatus


@pytest.fixture
def auth_headers(client, sample_driver):
    """Generate auth headers for the sample driver."""
    # Note: In a real integration test, we might call /auth/sync-google-user 
    # but for unit-scoped integration tests, we can often mock get_current_user_id 
    # OR if the test client is setup to bypass auth, use that.
    # Checking app/auth/dependencies.py might reveal how to bypass.
    
    # For now, let's assume we need a valid JWT or we mock the dependency.
    # In conftest.py, get_current_user_id is usually overridden or we use it.
    return {}


def test_nearby_path_search_api(client, sample_driver, db):
    """
    Test the GET /rides/nearby?role=path endpoint.
    """
    # 1. Create a ride with a route passing through a specific point
    # Vadodara -> Anand -> Ahmedabad
    route_wkt = "SRID=4326;LINESTRING(73.1812 22.3072, 73.0000 22.5500, 72.5714 23.0225)"
    ride = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Ahmedabad",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
        total_seats=4,
        available_seats=4,
        status=RideStatus.ACTIVE,
        route_geometry=route_wkt,
        price_per_seat=150
    )
    db.add(ride)
    db.commit()

    # 2. Search near the midpoint (Anand)
    # Midpoint: 22.5500, 73.0000
    response = client.get(
        "/rides/nearby",
        params={
            "lat": 22.5500,
            "lng": 73.0000,
            "radius_km": 5.0,
            "role": "path"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"] == "Vadodara"
    assert data[0]["destination"] == "Ahmedabad"


def test_nearby_path_search_api_no_match(client, sample_driver, db):
    """
    Test the GET /rides/nearby?role=path endpoint with a point far away.
    """
    route_wkt = "SRID=4326;LINESTRING(73.1812 22.3072, 73.0000 22.5500, 72.5714 23.0225)"
    ride = Ride(
        id=uuid4(),
        driver_id=sample_driver.id,
        source="Vadodara",
        destination="Ahmedabad",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
        total_seats=4,
        available_seats=4,
        status=RideStatus.ACTIVE,
        route_geometry=route_wkt,
        price_per_seat=150
    )
    db.add(ride)
    db.commit()

    # Search near a point ~60km away
    response = client.get(
        "/rides/nearby",
        params={
            "lat": 22.5500,
            "lng": 73.7000,
            "radius_km": 5.0,
            "role": "path"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
