import pytest

from app.bookings.models import Booking
from app.bookings.service import BookingService
from app.outbox.models import OutboxEvent


class TestBookingService:
    def test_create_booking_success(self, db, sample_ride, sample_passenger):
        initial_available_seats = sample_ride.available_seats

        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="test-key-1",
            correlation_id="test-corr-1",
        )

        assert booking is not None
        assert booking.status == "PENDING_PAYMENT"
        assert booking.trip_status.value == "BOOKED"
        assert booking.seats_booked == 2

        db.refresh(sample_ride)
        assert sample_ride.available_seats == initial_available_seats - 2

    def test_create_booking_insufficient_seats(self, db, sample_ride, sample_passenger):
        sample_ride.available_seats = 1
        db.commit()

        with pytest.raises(ValueError, match="Not enough seats available"):
            BookingService.create_booking(
                db=db,
                ride_id=sample_ride.id,
                passenger_id=sample_passenger.id,
                seats_requested=2,
                idempotency_key="test-key-2",
                correlation_id="test-corr-2",
            )

    def test_idempotency_retry_returns_same_booking(self, db, sample_ride, sample_passenger):
        idempotency_key = "test-key-3"

        booking1 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,
            correlation_id="test-corr-3",
        )

        booking2 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,
            correlation_id="test-corr-3",
        )

        assert booking1.id == booking2.id
        assert booking1.status == "PENDING_PAYMENT"
        assert booking2.status == "PENDING_PAYMENT"

        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3

    def test_duplicate_active_booking_fails(self, db, sample_ride, sample_passenger):
        BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-4",
            correlation_id="test-corr-4",
        )

        with pytest.raises(ValueError, match="already have an active booking"):
            BookingService.create_booking(
                db=db,
                ride_id=sample_ride.id,
                passenger_id=sample_passenger.id,
                seats_requested=1,
                idempotency_key="test-key-5",
                correlation_id="test-corr-5",
            )

    def test_rebook_cancelled_booking(self, db, sample_ride, sample_passenger):
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="test-key-6",
            correlation_id="test-corr-6",
        )

        booking.status = "CANCELLED"
        sample_ride.available_seats += 2
        db.commit()

        new_booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-7",
            correlation_id="test-corr-7",
        )

        assert new_booking.id == booking.id
        assert new_booking.status == "PENDING_PAYMENT"
        assert new_booking.seats_booked == 1
        assert new_booking.trip_status.value == "BOOKED"

        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3

    def test_outbox_event_created(self, db, sample_ride, sample_passenger):
        initial_event_count = db.query(OutboxEvent).count()

        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-9",
            correlation_id="test-corr-10",
        )

        events = db.query(OutboxEvent).filter(OutboxEvent.event_type == "booking.pending").all()

        assert len(events) == initial_event_count + 1
        latest_event = events[-1]
        assert str(booking.id) in str(latest_event.payload)
        assert latest_event.processed is False

    def test_mark_ready_requires_started_ride(self, db, sample_ride, sample_passenger):
        booking = Booking(
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_booked=1,
            status="PAID_HELD",
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        with pytest.raises(ValueError, match="Ride has not started yet"):
            BookingService.mark_ready(
                db=db,
                booking_id=str(booking.id),
                passenger_id=str(sample_passenger.id),
                correlation_id="ready-corr-1",
            )
