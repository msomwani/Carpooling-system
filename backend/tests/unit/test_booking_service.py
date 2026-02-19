import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.bookings.service import BookingService
from app.bookings.models import Booking
from app.rides.models import Ride
from app.users.models import User


class TestBookingService:
    """Unit tests for BookingService class."""
    
    def test_create_booking_success(self, db, sample_ride, sample_passenger):
        """Test successful booking creation."""
        # Arrange
        initial_available_seats = sample_ride.available_seats
        
        # Act
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="test-key-1",
            correlation_id="test-corr-1"
        )
        
        # Assert
        assert booking is not None
        assert booking.status == "CONFIRMED"
        assert booking.seats_booked == 2
        assert booking.ride_id == sample_ride.id
        assert booking.passenger_id == sample_passenger.id
        
        # Verify seat deduction
        db.refresh(sample_ride)
        assert sample_ride.available_seats == initial_available_seats - 2
    
    def test_create_booking_insufficient_seats(self, db, sample_ride, sample_passenger):
        """Test booking fails when not enough seats available."""
        # Arrange
        sample_ride.available_seats = 1
        db.commit()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Not enough seats available"):
            BookingService.create_booking(
                db=db,
                ride_id=sample_ride.id,
                passenger_id=sample_passenger.id,
                seats_requested=2,
                idempotency_key="test-key-2",
                correlation_id="test-corr-2"
            )
    
    def test_idempotency_retry_returns_same_booking(self, db, sample_ride, sample_passenger):
        """Test that retrying with same idempotency key returns same booking."""
        # Arrange
        idempotency_key = "test-key-3"
        
        # Act - Create booking first time
        booking1 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,
            correlation_id="test-corr-3"
        )
        
        # Act - Retry with same key
        booking2 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,
            correlation_id="test-corr-3"
        )
        
        # Assert - Should return same booking
        assert booking1.id == booking2.id
        assert booking1.status == "CONFIRMED"
        assert booking2.status == "CONFIRMED"
        
        # Verify seats were only deducted once
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3  # Started with 4, only 1 deducted
    
    def test_duplicate_confirmed_booking_fails(self, db, sample_ride, sample_passenger):
        """Test that passenger cannot have two confirmed bookings for same ride."""
        # Arrange - Create first booking
        BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-4",
            correlation_id="test-corr-4"
        )
        
        # Act & Assert - Try to create another booking
        with pytest.raises(ValueError, match="already have an active booking"):
            BookingService.create_booking(
                db=db,
                ride_id=sample_ride.id,
                passenger_id=sample_passenger.id,
                seats_requested=1,
                idempotency_key="test-key-5",  # Different key
                correlation_id="test-corr-5"
            )
    
    def test_rebook_cancelled_booking(self, db, sample_ride, sample_passenger):
        """Test that cancelled bookings can be rebooked."""
        # Arrange - Create and cancel a booking
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="test-key-6",
            correlation_id="test-corr-6"
        )
        
        # Cancel the booking
        booking.status = "CANCELLED"
        sample_ride.available_seats += 2  # Return seats
        db.commit()
        
        # Act - Rebook with different idempotency key
        new_booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-7",
            correlation_id="test-corr-7"
        )
        
        # Assert - Should reactivate the same booking
        assert new_booking.id == booking.id
        assert new_booking.status == "CONFIRMED"
        assert new_booking.seats_booked == 1
        
        # Verify seat deduction
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3  # 4 - 1
    
    def test_rebook_with_same_idempotency_key(self, db, sample_ride, sample_passenger):
        """Test rebooking cancelled booking with same idempotency key."""
        # Arrange - Create and cancel a booking
        idempotency_key = "test-key-8"
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,
            correlation_id="test-corr-8"
        )
        
        # Cancel the booking
        booking.status = "CANCELLED"
        sample_ride.available_seats += 1
        db.commit()
        
        # Act - Rebook with SAME idempotency key
        new_booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key=idempotency_key,  # Same key
            correlation_id="test-corr-9"
        )
        
        # Assert - Should reactivate and return CONFIRMED booking
        assert new_booking.id == booking.id
        assert new_booking.status == "CONFIRMED"
        assert new_booking.seats_booked == 1
    
    def test_outbox_event_created(self, db, sample_ride, sample_passenger):
        """Test that outbox event is created for booking."""
        from app.outbox.models import OutboxEvent
        
        # Arrange
        initial_event_count = db.query(OutboxEvent).count()
        
        # Act
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="test-key-9",
            correlation_id="test-corr-10"
        )
        
        # Assert
        events = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.confirmed"
        ).all()
        
        assert len(events) == initial_event_count + 1
        latest_event = events[-1]
        assert str(booking.id) in str(latest_event.payload)
        assert latest_event.processed == False