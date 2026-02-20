import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.auth.security import create_access_token
from app.bookings.history_model import BookingHistory
from app.bookings.models import Booking
from app.rides.models import Ride
from app.users.models import User


class TestAPIEndpoints:
    """Test API endpoints for correct HTTP responses."""
    
    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns data."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_signup_endpoint(self, client, db):
        """Test user signup endpoint."""
        response = client.post("/auth/signup", json={
            "name": "Test User",
            "email": f"testuser_{uuid4()}@test.com",
            "password": "securepassword123",
            "role": "passenger"
        })
        
        assert response.status_code == 200
        data = response.json()
        # Check that user ID is returned
        assert "id" in data
    
    def test_login_endpoint(self, client, db):
        """Test user login endpoint."""
        email = f"logintest_{uuid4()}@test.com"
        password = "testpassword123"
        
        # First signup
        client.post("/auth/signup", json={
            "name": "Login Test",
            "email": email,
            "password": password,
            "role": "passenger"
        })
        
        # Then login
        response = client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        
        assert response.status_code == 200
        # Cookie-based auth, so check for cookie or success message
        assert response.cookies or response.json().get("message") == "Logged in"
    
    def test_create_ride_as_driver(self, client, db):
        """Test creating a ride as a driver."""
        # Signup as driver
        email = f"driver_{uuid4()}@test.com"
        signup_response = client.post("/auth/signup", json={
            "name": "Test Driver",
            "email": email,
            "password": "driverpass123",
            "role": "driver"
        })
        assert signup_response.status_code == 200

        # Login to set auth cookie
        login_response = client.post("/auth/login", json={
            "email": email,
            "password": "driverpass123"
        })
        assert login_response.status_code == 200
        
        # Cookies are automatically handled by TestClient
        # Create ride (cookie auth happens automatically)
        response = client.post(
            "/rides/",
            json={
                "source": "City A",
                "destination": "City B",
                "departure_time": (datetime.now() + timedelta(hours=5)).isoformat(),
                "total_seats": 4
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "City A"
        assert data["destination"] == "City B"
        assert data["available_seats"] == 4
    
    def test_search_rides(self, client, db):
        """Test ride search endpoint."""
        # Just test that endpoint works and returns a list
        response = client.get("/rides/?source=A&destination=B")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_unauthorized_access_fails(self, client):
        """Test that endpoints require authentication."""
        # Clear any cookies first
        client.cookies.clear()
        
        # Try to create ride without auth
        response = client.post("/rides/", json={
            "source": "A",
            "destination": "B",
            "departure_time": datetime.now().isoformat(),
            "total_seats": 4
        })
        
        assert response.status_code == 401

    def test_analytics_overview_endpoint(self, client):
        """Test analytics overview endpoint."""
        response = client.get("/analytics/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_bookings" in data
        assert "cancellation_rate" in data
        assert "seat_utilization" in data
        assert "popular_routes" in data

    def test_booking_history_endpoint(self, client, db):
        """Test booking history endpoint returns projected events."""
        driver = User(
            id=uuid4(),
            name="History Driver",
            email=f"history_driver_{uuid4()}@test.com",
            password_hash="hashed",
            role="driver",
        )
        passenger = User(
            id=uuid4(),
            name="History Passenger",
            email=f"history_passenger_{uuid4()}@test.com",
            password_hash="hashed",
            role="passenger",
        )
        db.add(driver)
        db.add(passenger)
        db.flush()

        ride = Ride(
            id=uuid4(),
            driver_id=driver.id,
            source="HCity A",
            destination="HCity B",
            departure_time=datetime.now() + timedelta(hours=3),
            total_seats=3,
            available_seats=2,
        )
        db.add(ride)
        db.flush()

        booking = Booking(
            id=uuid4(),
            ride_id=ride.id,
            passenger_id=passenger.id,
            seats_booked=1,
            status="CONFIRMED",
        )
        db.add(booking)
        db.flush()

        history_row = BookingHistory(
            event_id=uuid4(),
            user_id=passenger.id,
            booking_id=booking.id,
            ride_id=ride.id,
            action="BOOKING_CONFIRMED",
            correlation_id="history-test-corr",
            details={"seats_booked": 1},
        )
        db.add(history_row)
        db.commit()

        token = create_access_token(subject=str(passenger.id))
        client.cookies.set("access_token", token)

        response = client.get("/bookings/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "BOOKING_CONFIRMED"
