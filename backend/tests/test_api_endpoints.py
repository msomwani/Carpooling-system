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
    
    def test_signup_endpoint(self, client):
        """Test user signup returns 201 and prompts for OTP verification."""
        response = client.post("/auth/signup", json={
            "name": "Test User",
            "email": f"testuser_{uuid4()}@test.com",
            "password": "securepassword123",
            "role": "passenger"
        })

        assert response.status_code == 201
        data = response.json()
        # New flow: returns message + email, not user ID
        assert "message" in data
        assert "email" in data
    
    def test_login_endpoint(self, client, db):
        """Test login works after email is verified."""
        from app.users.models import User as UserModel
        from app.auth.security import hash_password

        email = f"logintest_{uuid4()}@test.com"
        password = "testpassword123"

        # Create a pre-verified user directly in the DB (bypasses OTP flow)
        user = UserModel(
            id=uuid4(),
            name="Login Test",
            email=email,
            password_hash=hash_password(password),
            role="passenger",
            is_email_verified=True,
        )
        db.add(user)
        db.commit()

        # Login should succeed
        response = client.post("/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        assert response.json().get("message") == "Logged in"
    
    def test_create_ride_as_driver(self, client, db):
        """Test creating a ride as a driver (pre-verified account)."""
        from app.users.models import User as UserModel
        from app.auth.security import hash_password

        email = f"driver_{uuid4()}@test.com"
        password = "driverpass123"

        # Create pre-verified driver directly in DB
        driver = UserModel(
            id=uuid4(),
            name="Test Driver",
            email=email,
            password_hash=hash_password(password),
            role="driver",
            is_email_verified=True,
        )
        db.add(driver)
        db.commit()

        # Login
        login_response = client.post("/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200

        # Create ride
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

    def test_verify_otp_endpoint(self, client, db):
        """Test that OTP verification marks email as verified and logs in."""
        from app.users.models import User as UserModel
        from app.auth.security import hash_password

        email = f"otptest_{uuid4()}@test.com"
        # Create unverified user with known OTP
        from datetime import timezone as tz
        user = UserModel(
            id=uuid4(),
            name="OTP Test",
            email=email,
            password_hash=hash_password("pass123"),
            role="passenger",
            is_email_verified=False,
            otp_code="123456",
            otp_expires_at=datetime.now(tz.utc) + timedelta(minutes=10),
        )
        db.add(user)
        db.commit()

        response = client.post("/auth/verify-otp", json={"email": email, "otp": "123456"})
        assert response.status_code == 200
        assert "verified" in response.json().get("message", "").lower()

    def test_login_rejects_unverified_email(self, client, db):
        """Test that login is rejected when email is not verified."""
        from app.users.models import User as UserModel
        from app.auth.security import hash_password

        email = f"unverified_{uuid4()}@test.com"
        user = UserModel(
            id=uuid4(),
            name="Unverified User",
            email=email,
            password_hash=hash_password("pass123"),
            role="passenger",
            is_email_verified=False,
        )
        db.add(user)
        db.commit()

        response = client.post("/auth/login", json={"email": email, "password": "pass123"})
        assert response.status_code == 403  # forbidden until verified

    def test_resend_otp_endpoint(self, client, db):
        """Test resend OTP sends a fresh code."""
        from app.users.models import User as UserModel
        from app.auth.security import hash_password

        email = f"resend_{uuid4()}@test.com"
        user = UserModel(
            id=uuid4(),
            name="Resend Test",
            email=email,
            password_hash=hash_password("pass123"),
            role="passenger",
            is_email_verified=False,
            otp_code="000000",
        )
        db.add(user)
        db.commit()

        response = client.post("/auth/resend-otp", json={"email": email})
        assert response.status_code == 200
        assert "sent" in response.json().get("message", "").lower()

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

    def test_maps_api_key_endpoint(self, client):
        """Test maps API key endpoint returns a key."""
        response = client.get("/maps/api-key")
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert isinstance(data["api_key"], str)

    def test_nearby_rides_returns_results(self, client, db):
        """Test nearby ride search returns rides within radius."""
        # Create driver + ride with coordinates
        driver = User(
            id=uuid4(),
            name="Nearby Driver",
            email=f"nearby_driver_{uuid4()}@test.com",
            password_hash="hashed",
            role="driver",
        )
        db.add(driver)
        db.flush()

        ride = Ride(
            id=uuid4(),
            driver_id=driver.id,
            source="Vadodara Railway Station",
            source_lat=22.3101,
            source_lng=73.1810,
            destination="Halol GIDC",
            destination_lat=22.5100,
            destination_lng=73.4600,
            departure_time=datetime.now() + timedelta(hours=3),
            total_seats=4,
            available_seats=4,
        )
        db.add(ride)
        db.commit()

        # Search near Vadodara (should find the ride within 5km)
        response = client.get(
            "/rides/nearby?lat=22.3100&lng=73.1800&radius_km=5&role=source"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["source"] == "Vadodara Railway Station"

    def test_nearby_rides_empty_when_out_of_range(self, client, db):
        """Test nearby ride search returns empty when no rides in range."""
        # Create driver + ride in Vadodara
        driver = User(
            id=uuid4(),
            name="Far Driver",
            email=f"far_driver_{uuid4()}@test.com",
            password_hash="hashed",
            role="driver",
        )
        db.add(driver)
        db.flush()

        ride = Ride(
            id=uuid4(),
            driver_id=driver.id,
            source="Vadodara Railway Station",
            source_lat=22.3101,
            source_lng=73.1810,
            destination="Halol GIDC",
            destination_lat=22.5100,
            destination_lng=73.4600,
            departure_time=datetime.now() + timedelta(hours=3),
            total_seats=4,
            available_seats=4,
        )
        db.add(ride)
        db.commit()

        # Search near Mumbai (far away, should find nothing)
        response = client.get(
            "/rides/nearby?lat=19.0760&lng=72.8777&radius_km=10&role=source"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_nearby_rides_missing_params(self, client):
        """Test nearby ride search returns 422 when required params missing."""
        response = client.get("/rides/nearby")
        assert response.status_code == 422
