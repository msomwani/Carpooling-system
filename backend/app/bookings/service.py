import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.rides.models import Ride
from app.bookings.models import Booking
from app.bookings.idempotency_model import BookingIdempotency
from app.outbox.models import OutboxEvent

logger = logging.getLogger(__name__)


class BookingService:

    @staticmethod
    def create_booking(
        db: Session,
        *,
        ride_id,
        passenger_id,
        seats_requested: int,
        idempotency_key: str,
        correlation_id: str,
    ):
        logger.info(
            "Processing booking request",
            extra={"correlation_id": correlation_id},
        )

        # 1️⃣ Idempotency check
        idempo = (
            db.query(BookingIdempotency)
            .filter(BookingIdempotency.idempotency_key == idempotency_key)
            .first()
        )

        if idempo and idempo.booking_id:
            logger.info(
                "Idempotent retry detected",
                extra={"correlation_id": correlation_id},
            )
            return db.get(Booking, idempo.booking_id)

        if not idempo:
            idempo = BookingIdempotency(idempotency_key=idempotency_key)
            db.add(idempo)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                idempo = (
                    db.query(BookingIdempotency)
                    .filter(BookingIdempotency.idempotency_key == idempotency_key)
                    .first()
                )

        try:
            # 2️⃣ Lock ride row
            ride = (
                db.query(Ride)
                .filter(Ride.id == ride_id)
                .with_for_update()
                .one()
            )

            if ride.available_seats < seats_requested:
                raise ValueError("Not enough seats available")

            ride.available_seats -= seats_requested

            booking = Booking(
                id=uuid4(),
                ride_id=ride_id,
                passenger_id=passenger_id,
                seats_booked=seats_requested,
                status="CONFIRMED",
            )

            db.add(booking)
            db.flush()

            idempo.booking_id = booking.id

            #Write event to Outbox WITH correlation_id
            outbox_event = OutboxEvent(
                event_type="booking.confirmed",
                payload={
                    "booking_id": str(booking.id),
                    "ride_id": str(booking.ride_id),
                    "passenger_id": str(booking.passenger_id),
                    "correlation_id": correlation_id, 
                },
            )

            db.add(outbox_event)

            db.commit()

            logger.info(
                "Booking committed successfully",
                extra={"correlation_id": correlation_id},
            )

        except Exception:
            db.rollback()
            logger.exception(
                "Booking transaction failed",
                extra={"correlation_id": correlation_id},
            )
            raise

        return booking
