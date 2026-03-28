import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.rides.service import RideService
from app.bookings.service import BookingService
from app.bookings.cancel_service import CancellationService
from app.outbox.models import OutboxEvent
from app.notifications.service import NotificationService

class TestNotificationEvents:
    """Tests the generation of OutboxEvents for notification triggers."""

    def test_ride_created_event(self, db, sample_driver):
        departure = datetime.now(timezone.utc) + timedelta(days=1)
        ride = RideService.create_ride(
            db,
            driver_id=sample_driver.id,
            source="Alkapuri",
            destination="Makarpura",
            departure_time=departure,
            total_seats=4
        )

        event = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "ride.created"
        ).first()

        assert event is not None
        assert event.payload["ride_id"] == str(ride.id)
        assert event.payload["driver_id"] == str(sample_driver.id)

    def test_booking_confirmed_event(self, db, sample_ride, sample_passenger):
        BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="notif-test-1",
            correlation_id="notif-corr-1"
        )

        event = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.confirmed"
        ).first()

        assert event is not None
        assert event.payload["passenger_id"] == str(sample_passenger.id)

    def test_booking_cancelled_event(self, db, sample_ride, sample_passenger):
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="notif-test-2",
            correlation_id="notif-corr-2"
        )

        CancellationService.cancel_booking(
            db=db,
            booking_id=str(booking.id),
            user_id=str(sample_passenger.id),
            correlation_id="notif-corr-3"
        )

        event = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.cancelled"
        ).first()

        assert event is not None
        assert event.payload["booking_id"] == str(booking.id)

    def test_ride_cancelled_events(self, db, sample_ride, sample_passenger, sample_driver):
        # 1. Passenger books
        BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="notif-test-3",
            correlation_id="notif-corr-4"
        )

        # 2. Driver cancels ride
        RideService.cancel_ride(
            db=db,
            ride_id=str(sample_ride.id),
            driver_id=str(sample_driver.id),
            correlation_id="notif-corr-5"
        )

        # 3. Verify driver cancellation event (no refund as creation is free)
        driver_event = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "ride.cancelled"
        ).first()
        assert driver_event is not None

        # 4. Verify passenger alert event
        passenger_event = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.cancelled_by_driver"
        ).first()
        assert passenger_event is not None
        assert passenger_event.payload["passenger_id"] == str(sample_passenger.id)

    def test_notification_service_logic(self, db, sample_passenger):
        """Verify NotificationService correctly filters and 'sends' (prints)."""
        with patch("builtins.print") as mock_print:
            NotificationService.send_booking_confirmed(db, str(sample_passenger.id), str(uuid4()))
            
            # Should have printed the notification
            mock_print.assert_called()
            args, _ = mock_print.call_args
            assert "[Notification]" in args[0]
            assert sample_passenger.email in args[0]
