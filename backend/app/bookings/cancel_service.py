import logging
from sqlalchemy.orm import Session
from app.bookings.models import Booking
from app.rides.models import Ride
from app.outbox.models import OutboxEvent

logger = logging.getLogger(__name__)


class CancellationService:

    @staticmethod
    def cancel_booking(
        db: Session,
        *,
        booking_id: str,
        user_id: str,
        correlation_id: str,
    ):
        logger.info(
            "Processing cancellation request",
            extra={"correlation_id": correlation_id},
        )

        booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id)
            .with_for_update()
            .first()
        )

        if not booking:
            raise ValueError("Booking not found")

        if str(booking.passenger_id) != str(user_id):
            raise ValueError("Not authorized to cancel this booking")

        if booking.status == "CANCELLED":
            raise ValueError("Booking already cancelled")

        ride = (
            db.query(Ride)
            .filter(Ride.id == booking.ride_id)
            .with_for_update()
            .first()
        )

        ride.available_seats += booking.seats_booked
        booking.status = "CANCELLED"

        #Write compensating event WITH correlation_id
        outbox_event = OutboxEvent(
            event_type="booking.cancelled",
            payload={
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "correlation_id": correlation_id,  # 🔥 critical
            },
        )

        db.add(outbox_event)

        db.commit()

        logger.info(
            "Cancellation committed successfully",
            extra={"correlation_id": correlation_id},
        )

        return booking
