import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from app.rides.service import RideService
from app.rides.models import Ride, RideStatus

from app.vehicles.models import Vehicle, VehicleType

class TestRideService:
    @pytest.fixture
    def sample_vehicle(self, db, sample_driver):
        """Create a sample vehicle for testing."""
        vehicle = Vehicle(
            id=uuid4(),
            owner_id=sample_driver.id,
            make="Toyota",
            model="Camry",
            color="Silver",
            license_plate=f"TEST-{uuid4().hex[:6].upper()}",
            type=VehicleType.CAR
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    def test_complete_ride_before_departure_fails(self, db, sample_ride):
        """Issue 4: Verify that a ride cannot be completed before its departure time."""
        # Arrange: Set departure time in the future
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot complete a ride before its departure time"):
            RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id
            )
            
    def test_complete_ride_after_departure_success(self, db, sample_ride):
        """Issue 4: Verify that a ride can be completed after its departure time."""
        # Arrange: Set departure time in the past
        sample_ride.departure_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        
        # Act
        with patch("app.common.redis.invalidate_rides_cache") as mock_invalidate:
            ride = RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id
            )
            
            # Assert
            assert ride.status == RideStatus.COMPLETED
            mock_invalidate.assert_called_once()  # Verify Issue 3
            
    def test_cache_invalidated_on_ride_creation(self, db, sample_driver, sample_vehicle):
        """Issue 3: Verify cache is invalidated when a new ride is created."""
        with patch("app.common.redis.invalidate_rides_cache") as mock_invalidate:
            RideService.create_ride(
                db=db,
                driver_id=sample_driver.id,
                source="Start",
                source_lat=0.0,
                source_lng=0.0,
                destination="End",
                destination_lat=1.0,
                destination_lng=1.0,
                departure_time=datetime.now(timezone.utc) + timedelta(days=1),
                total_seats=4,
                price_per_seat=100,
                vehicle_id=sample_vehicle.id
            )
            mock_invalidate.assert_called_once()

    def test_create_ride_invalid_seats(self, db, sample_driver, sample_vehicle):
        """Issue 8: Verify that creating a ride with <= 0 seats fails."""
        with pytest.raises(ValueError, match="Total seats must be greater than zero"):
            RideService.create_ride(
                db=db,
                driver_id=sample_driver.id,
                source="Start",
                destination="End",
                total_seats=0,
                vehicle_id=sample_vehicle.id
            )
