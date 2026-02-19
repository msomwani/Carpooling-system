import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.bookings.service import BookingService
from app.bookings.cancel_service import CancellationService
from app.rides.models import Ride
from app.bookings.models import Booking
from app.outbox.models import OutboxEvent


class TestBookingFlow:
    """Integration tests for complete booking lifecycle."""
    
    def test_complete_booking_flow(self, db, sample_ride, sample_passenger):
        """Test complete flow: book → verify → cancel → verify."""
        # Step 1: Book a ride
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="flow-test-1",
            correlation_id="flow-corr-1"
        )
        
        assert booking.status == "CONFIRMED"
        assert booking.seats_booked == 2
        
        # Verify seat deduction
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 2  # Started with 4
        
        # Verify outbox event created
        confirmed_events = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.confirmed"
        ).count()
        assert confirmed_events >= 1
        
        # Step 2: Cancel the booking
        cancelled_booking = CancellationService.cancel_booking(
            db=db,
            booking_id=str(booking.id),
            user_id=str(sample_passenger.id),
            correlation_id="flow-corr-2"
        )
        
        assert cancelled_booking.status == "CANCELLED"
        
        # Verify seats returned
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 4  # Back to original
        
        # Verify cancellation outbox event created
        cancelled_events = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.cancelled"
        ).count()
        assert cancelled_events >= 1
    
    def test_book_cancel_rebook_flow(self, db, sample_ride, sample_passenger):
        """Test flow: book → cancel → rebook same ride."""
        # Step 1: Initial booking
        booking1 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="rebook-test-1",
            correlation_id="rebook-corr-1"
        )
        
        assert booking1.status == "CONFIRMED"
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3
        
        # Step 2: Cancel booking
        CancellationService.cancel_booking(
            db=db,
            booking_id=str(booking1.id),
            user_id=str(sample_passenger.id),
            correlation_id="rebook-corr-2"
        )
        
        db.refresh(booking1)
        assert booking1.status == "CANCELLED"
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 4
        
        # Step 3: Rebook the same ride
        booking2 = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=2,
            idempotency_key="rebook-test-2",
            correlation_id="rebook-corr-3"
        )
        
        # Should reactivate the same booking record
        assert booking2.id == booking1.id
        assert booking2.status == "CONFIRMED"
        assert booking2.seats_booked == 2
        
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 2
    
    def test_multiple_passengers_booking_same_ride(self, db, sample_ride):
        """Test multiple passengers can book the same ride (non-concurrent)."""
        from app.users.models import User
        
        # Create 3 passengers
        passengers = []
        for i in range(3):
            passenger = User(
                id=uuid4(),
                name=f"Passenger {i}",
                email=f"p{i}@test.com",
                password_hash="hash",
                role="passenger"
            )
            db.add(passenger)
            passengers.append(passenger)
        db.commit()
        
        # Each passenger books 1 seat
        bookings = []
        for i, passenger in enumerate(passengers):
            booking = BookingService.create_booking(
                db=db,
                ride_id=sample_ride.id,
                passenger_id=passenger.id,
                seats_requested=1,
                idempotency_key=f"multi-test-{i}",
                correlation_id=f"multi-corr-{i}"
            )
            bookings.append(booking)
        
        # Verify all bookings successful
        assert len(bookings) == 3
        for booking in bookings:
            assert booking.status == "CONFIRMED"
        
        # Verify correct seat deduction
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 1  # Started with 4, 3 booked
    
    def test_cannot_cancel_others_booking(self, db, sample_ride, sample_passenger):
        """Test that users cannot cancel other users' bookings."""
        from app.users.models import User
        
        # Create another passenger
        other_passenger = User(
            id=uuid4(),
            name="Other Passenger",
            email="other@test.com",
            password_hash="hash",
            role="passenger"
        )
        db.add(other_passenger)
        db.commit()
        
        # Passenger 1 books
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="cancel-test-1",
            correlation_id="cancel-corr-1"
        )
        
        # Passenger 2 tries to cancel passenger 1's booking
        with pytest.raises(ValueError, match="Not authorized"):
            CancellationService.cancel_booking(
                db=db,
                booking_id=str(booking.id),
                user_id=str(other_passenger.id),
                correlation_id="cancel-corr-2"
            )
    
    def test_cannot_cancel_already_cancelled_booking(self, db, sample_ride, sample_passenger):
        """Test that already cancelled bookings cannot be cancelled again."""
        # Create and cancel booking
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="double-cancel-1",
            correlation_id="double-cancel-corr-1"
        )
        
        CancellationService.cancel_booking(
            db=db,
            booking_id=str(booking.id),
            user_id=str(sample_passenger.id),
            correlation_id="double-cancel-corr-2"
        )
        
        # Try to cancel again
        with pytest.raises(ValueError, match="already cancelled"):
            CancellationService.cancel_booking(
                db=db,
                booking_id=str(booking.id),
                user_id=str(sample_passenger.id),
                correlation_id="double-cancel-corr-3"
            )
    
    def test_booking_creates_correlation_chain(self, db, sample_ride, sample_passenger):
        """Test that correlation IDs are properly tracked across events."""
        correlation_id = "chain-test-correlation-123"
        
        # Create booking
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="chain-test-1",
            correlation_id=correlation_id
        )
        
        # Check outbox event has correlation ID
        events = db.query(OutboxEvent).filter(
            OutboxEvent.event_type == "booking.confirmed"
        ).all()
        
        # Find the event for this booking
        booking_event = None
        for event in events:
            if event.payload.get('booking_id') == str(booking.id):
                booking_event = event
                break
        
        assert booking_event is not None
        assert booking_event.payload.get('correlation_id') == correlation_id