import logging
from sqlalchemy.orm import Session
from app.bookings.models import Booking
from app.rides.models import Ride
from app.outbox.models import OutboxEvent
from app.common.redis import redis_client
from datetime import datetime, timezone

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

        if ride.departure_time:
            now = datetime.now(timezone.utc)
            if ride.departure_time < now:
                raise ValueError("Cannot cancel booking for a ride that has already departed")

        ride.available_seats += booking.seats_booked
        booking.status = "CANCELLED"

        # Write compensating event WITH correlation_id
        outbox_event = OutboxEvent(
            event_type="booking.cancelled",
            payload={
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "seats_returned": booking.seats_booked,
                "correlation_id": correlation_id,
            },
        )

        db.add(outbox_event)

        db.commit()

        #Invalidate Redis cache after successful cancellation
        try:
            cache_pattern = "rides:*"
            for key in redis_client.scan_iter(match=cache_pattern):
                redis_client.delete(key)
            logger.info(
                "Cache invalidated after booking cancellation",
                extra={"correlation_id": correlation_id},
            )
        except Exception as cache_error:
            # Log but don't fail the cancellation if cache invalidation fails
            logger.warning(
                f"Failed to invalidate cache: {cache_error}",
                extra={"correlation_id": correlation_id},
            )

        logger.info(
            "Cancellation committed successfully",
            extra={"correlation_id": correlation_id},
        )

        return booking