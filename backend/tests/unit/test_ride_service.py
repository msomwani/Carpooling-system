import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.bookings.models import Booking, BookingTripStatus
from app.rides.models import RideCompletionSource, RideStatus
from app.rides.service import RideService
from app.vehicles.models import Vehicle, VehicleType


class TestRideService:
    @pytest.fixture
    def sample_vehicle(self, db, sample_driver):
        vehicle = Vehicle(
            id=uuid4(),
            owner_id=sample_driver.id,
            make="Toyota",
            model="Camry",
            color="Silver",
            license_plate=f"TEST-{uuid4().hex[:6].upper()}",
            type=VehicleType.CAR,
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    def test_start_ride_before_window_fails(self, db, sample_ride):
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(hours=2)
        db.commit()

        with pytest.raises(ValueError, match="Ride can only be started"):
            RideService.start_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.source_lat,
                lng=sample_ride.source_lng,
            )

    def test_start_ride_near_source_success(self, db, sample_ride):
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.commit()

        with patch("app.common.redis.invalidate_rides_cache") as mock_invalidate:
            ride = RideService.start_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.source_lat,
                lng=sample_ride.source_lng,
            )

        assert ride.status == RideStatus.STARTED
        assert ride.actual_started_at is not None
        assert ride.actual_start_lat == sample_ride.source_lat
        mock_invalidate.assert_called_once()

    def test_complete_ride_requires_started_status(self, db, sample_ride):
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.commit()

        with pytest.raises(ValueError, match="Ride must be started"):
            RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.destination_lat,
                lng=sample_ride.destination_lng,
            )

    def test_complete_ride_after_start_success(self, db, sample_ride):
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.commit()

        RideService.start_ride(
            db=db,
            ride_id=sample_ride.id,
            driver_id=sample_ride.driver_id,
            lat=sample_ride.source_lat,
            lng=sample_ride.source_lng,
        )

        with patch("app.common.redis.invalidate_rides_cache") as mock_invalidate:
            ride = RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.destination_lat,
                lng=sample_ride.destination_lng,
            )

        assert ride.status == RideStatus.COMPLETED
        assert ride.completed_by == RideCompletionSource.DRIVER
        assert ride.actual_completed_at is not None
        assert mock_invalidate.call_count == 1

    def test_cache_invalidated_on_ride_creation(self, db, sample_driver, sample_vehicle):
        with patch("app.common.redis.invalidate_rides_cache") as mock_invalidate:
            RideService.create_ride(
                db=db,
                driver_id=sample_driver.id,
                source="Start",
                source_lat=22.3072,
                source_lng=73.1812,
                destination="End",
                destination_lat=22.4961,
                destination_lng=73.4622,
                departure_time=datetime.now(timezone.utc) + timedelta(days=1),
                total_seats=4,
                price_per_seat=100,
                vehicle_id=sample_vehicle.id,
            )
            mock_invalidate.assert_called_once()

    def test_create_ride_invalid_seats(self, db, sample_driver, sample_vehicle):
        with pytest.raises(ValueError, match="Total seats must be greater than zero"):
            RideService.create_ride(
                db=db,
                driver_id=sample_driver.id,
                source="Start",
                destination="End",
                total_seats=0,
                vehicle_id=sample_vehicle.id,
            )

    def test_complete_ride_releases_transfer_after_settlement(self, db, sample_ride, sample_driver, sample_passenger):
        sample_driver.razorpay_account_id = "acc_test_driver"
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        booking = Booking(
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="PAID_HELD",
            trip_status=BookingTripStatus.BOARDED,
            boarded_seats=1,
            razorpay_payment_id="pay_test_123",
        )
        db.add(booking)
        db.commit()

        RideService.start_ride(
            db=db,
            ride_id=sample_ride.id,
            driver_id=sample_ride.driver_id,
            lat=sample_ride.source_lat,
            lng=sample_ride.source_lng,
        )

        payment_service = MagicMock()
        payment_service.create_transfer.return_value = {"items": [{"id": "trf_test_123"}]}

        with patch("app.payments.service.PaymentService", return_value=payment_service), patch(
            "app.common.redis.invalidate_rides_cache"
        ):
            ride = RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.destination_lat,
                lng=sample_ride.destination_lng,
            )

        db.refresh(booking)
        assert ride.status == RideStatus.COMPLETED
        assert booking.status == "CONFIRMED"
        assert booking.razorpay_transfer_id == "trf_test_123"
        payment_service.create_transfer.assert_called_once()
        payment_service.release_transfer.assert_called_once_with("trf_test_123")

    def test_complete_ride_skips_duplicate_transfer_when_transfer_id_exists(self, db, sample_ride, sample_driver, sample_passenger):
        sample_driver.razorpay_account_id = "acc_test_driver"
        sample_ride.departure_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        booking = Booking(
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="PAID_HELD",
            trip_status=BookingTripStatus.BOARDED,
            boarded_seats=1,
            razorpay_payment_id="pay_test_456",
            razorpay_transfer_id="trf_existing_456",
        )
        db.add(booking)
        db.commit()

        RideService.start_ride(
            db=db,
            ride_id=sample_ride.id,
            driver_id=sample_ride.driver_id,
            lat=sample_ride.source_lat,
            lng=sample_ride.source_lng,
        )

        payment_service = MagicMock()

        with patch("app.payments.service.PaymentService", return_value=payment_service), patch(
            "app.common.redis.invalidate_rides_cache"
        ):
            RideService.complete_ride(
                db=db,
                ride_id=sample_ride.id,
                driver_id=sample_ride.driver_id,
                lat=sample_ride.destination_lat,
                lng=sample_ride.destination_lng,
            )

        payment_service.create_transfer.assert_not_called()
        payment_service.release_transfer.assert_called_once_with("trf_existing_456")
