import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from uuid import uuid4

from app.rides.models import Ride
from app.rides.service import RideService
from app.bookings.models import Booking
from app.bookings.idempotency_model import BookingIdempotency
from app.outbox.models import OutboxEvent
from app.common.metrics import increment
from app.common.redis import redis_client

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

        if seats_requested <= 0:
            raise ValueError("Requested seats must be greater than zero")

        # 1️⃣ Idempotency check
        idempotency_record = (
            db.query(BookingIdempotency)
            .filter(BookingIdempotency.idempotency_key == idempotency_key)
            .first()
        )

        # If idempotency record exists and has a booking_id
        if idempotency_record and idempotency_record.booking_id:
            existing_booking = db.get(Booking, idempotency_record.booking_id)
            
            # If the booking is CONFIRMED, return it (true idempotent retry)
            if existing_booking and existing_booking.status == "CONFIRMED":
                logger.info(
                    "Idempotent retry detected - returning confirmed booking",
                    extra={"correlation_id": correlation_id},
                )
                increment("booking_idempotent_retry_total")
                return existing_booking
            
            # If the booking is CANCELLED, allow rebooking by clearing the idempotency link
            if existing_booking and existing_booking.status == "CANCELLED":
                logger.info(
                    "Previous booking was cancelled - allowing rebooking",
                    extra={"correlation_id": correlation_id},
                )
                idempotency_record.booking_id = None  # Clear the link to allow rebooking
                db.flush()

        # Create idempotency record if it doesn't exist
        if not idempotency_record:
            idempotency_record = BookingIdempotency(idempotency_key=idempotency_key)
            db.add(idempotency_record)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                idempotency_record = (
                    db.query(BookingIdempotency)
                    .filter(BookingIdempotency.idempotency_key == idempotency_key)
                    .first()
                )
                if idempotency_record and idempotency_record.booking_id:
                    existing_booking = db.get(Booking, idempotency_record.booking_id)
                    if existing_booking and existing_booking.status == "CONFIRMED":
                        logger.info(
                            "Idempotent retry detected after race - returning confirmed booking",
                            extra={"correlation_id": correlation_id},
                        )
                        increment("booking_idempotent_retry_total")
                        return existing_booking

        try:
            # 2️⃣ Lock ride row
            ride = (
                db.query(Ride)
                .filter(Ride.id == ride_id)
                .with_for_update()
                .one()
            )

            # 🚫 Drivers cannot book their own ride
            if str(ride.driver_id) == str(passenger_id):
                increment("booking_failure_total")
                raise ValueError("Drivers cannot book their own ride")

            # 🚫 Cannot book rides that have already departed
            if ride.departure_time:
                now = datetime.now(timezone.utc)
                dept = ride.departure_time
                if dept.tzinfo is None:
                    dept = dept.replace(tzinfo=timezone.utc)
                if dept < now:
                    increment("booking_failure_total")
                    raise ValueError("Cannot book a ride that has already departed")

                # 🚫 Check for overlapping schedules (double-booking)
                try:
                    RideService._check_overlapping_rides(db, passenger_id, ride.departure_time)
                except ValueError as e:
                    increment("booking_failure_total")
                    raise ValueError(str(e))

            # 3️⃣ Check for existing booking to prevent duplicates or resume payment
            existing_booking = (
                db.query(Booking)
                .filter(
                    Booking.ride_id == ride_id,
                    Booking.passenger_id == passenger_id,
                    Booking.status.in_(["PENDING_PAYMENT", "PAID_HELD", "CONFIRMED"]),
                )
                .first()
            )
            
            if existing_booking:
                if existing_booking.status == "PENDING_PAYMENT":
                    logger.info(
                        "Returning existing pending booking",
                        extra={"correlation_id": correlation_id},
                    )
                    return existing_booking
                
                increment("booking_failure_total")
                raise ValueError("You already have an active booking for this ride")

            # 4️⃣ Check for existing CANCELLED booking to reactivate
            cancelled_booking = (
                db.query(Booking)
                .filter(
                    Booking.ride_id == ride_id,
                    Booking.passenger_id == passenger_id,
                    Booking.status == "CANCELLED"
                )
                .first()
            )

            if cancelled_booking:
                # Reactivate the cancelled booking
                logger.info(
                    f"Reactivating cancelled booking {cancelled_booking.id}",
                    extra={"correlation_id": correlation_id},
                )
                
                # Check seat availability
                if ride.available_seats < seats_requested:
                    increment("booking_failure_total")
                    raise ValueError("Not enough seats available")
                
                ride.available_seats -= seats_requested
                # Recative it as PENDING_PAYMENT to force payment again
                cancelled_booking.status = "PENDING_PAYMENT"
                cancelled_booking.seats_booked = seats_requested
                
                db.flush()
                idempotency_record.booking_id = cancelled_booking.id

                # Outbox event
                outbox_event = OutboxEvent(
                    event_type="booking.pending",
                    payload={
                        "booking_id": str(cancelled_booking.id),
                        "ride_id": str(cancelled_booking.ride_id),
                        "passenger_id": str(cancelled_booking.passenger_id),
                        "correlation_id": correlation_id,
                        "reactivated": True,
                    },
                )
                db.add(outbox_event)
                db.commit()
                
                # Invalidate Redis cache
                from app.common.redis import invalidate_rides_cache
                invalidate_rides_cache()
                
                increment("booking_success_total")
                increment("booking_reactivated_total")
                
                return cancelled_booking

            # 5️⃣ Create new booking if none exists
            if ride.available_seats < seats_requested:
                increment("booking_failure_total")
                raise ValueError("Not enough seats available")

            ride.available_seats -= seats_requested

            booking = Booking(
                id=uuid4(),
                ride_id=ride_id,
                passenger_id=passenger_id,
                seats_booked=seats_requested,
                status="PENDING_PAYMENT",
            )

            db.add(booking)
            db.flush()

            idempotency_record.booking_id = booking.id

            # Outbox event with correlation ID
            outbox_event = OutboxEvent(
                event_type="booking.pending",
                payload={
                    "booking_id": str(booking.id),
                    "ride_id": str(booking.ride_id),
                    "passenger_id": str(booking.passenger_id),
                    "correlation_id": correlation_id,
                },
            )

            db.add(outbox_event)
            db.commit()
            
            # Invalidate Redis cache
            from app.common.redis import invalidate_rides_cache
            invalidate_rides_cache()
            
            increment("booking_success_total")

            logger.info(
                "Booking created in PENDING_PAYMENT status",
                extra={"correlation_id": correlation_id},
            )
            return booking
            # 🔥 Invalidate Redis cache after successful booking
            from app.common.redis import invalidate_rides_cache
            invalidate_rides_cache()
            
            increment("booking_success_total")

            logger.info(
                "Booking committed successfully",
                extra={"correlation_id": correlation_id},
            )

        except Exception:
            db.rollback()
            increment("booking_failure_total")
            logger.exception(
                "Booking transaction failed",
                extra={"correlation_id": correlation_id},
            )
            raise

        return booking
