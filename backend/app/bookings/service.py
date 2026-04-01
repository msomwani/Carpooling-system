import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.bookings.idempotency_model import BookingIdempotency
from app.bookings.models import Booking, BookingTripStatus
from app.common.metrics import increment
from app.outbox.models import OutboxEvent
from app.rides.models import Ride, RideStatus
from app.rides.service import RideService

logger = logging.getLogger(__name__)

_ACTIVE_BOOKING_STATUSES = ["PENDING_PAYMENT", "PAID_HELD", "CONFIRMED"]


class BookingService:
    @staticmethod
    def _queue_event(db: Session, event_type: str, payload: dict):
        db.add(OutboxEvent(event_type=event_type, payload=payload))

    @staticmethod
    def _get_booking_for_passenger(
        db: Session,
        *,
        booking_id: str,
        passenger_id: str,
        with_lock: bool = False,
    ) -> tuple[Booking, Ride]:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")
        if str(booking.passenger_id) != str(passenger_id):
            raise ValueError("Not authorized")

        ride_query = db.query(Ride).filter(Ride.id == booking.ride_id)
        if with_lock:
            ride_query = ride_query.with_for_update()
        ride = ride_query.first()
        if not ride:
            raise ValueError("Ride not found")

        if with_lock:
            booking = (
                db.query(Booking)
                .filter(Booking.id == booking_id)
                .with_for_update()
                .first()
            )
            if not booking:
                raise ValueError("Booking not found")
            if str(booking.passenger_id) != str(passenger_id):
                raise ValueError("Not authorized")
        return booking, ride

    @staticmethod
    def _get_booking_for_driver(
        db: Session,
        *,
        booking_id: str,
        driver_id: str,
        with_lock: bool = False,
    ) -> tuple[Booking, Ride]:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")

        ride_query = db.query(Ride).filter(Ride.id == booking.ride_id)
        if with_lock:
            ride_query = ride_query.with_for_update()
        ride = ride_query.first()
        if not ride:
            raise ValueError("Ride not found")
        if str(ride.driver_id) != str(driver_id):
            raise PermissionError("You are not the driver of this ride")

        if with_lock:
            booking = (
                db.query(Booking)
                .filter(Booking.id == booking_id)
                .with_for_update()
                .first()
            )
            if not booking:
                raise ValueError("Booking not found")
        return booking, ride

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
        logger.info("Processing booking request", extra={"correlation_id": correlation_id})

        if seats_requested <= 0:
            raise ValueError("Requested seats must be greater than zero")

        idempotency_record = (
            db.query(BookingIdempotency)
            .filter(BookingIdempotency.idempotency_key == idempotency_key)
            .first()
        )

        if idempotency_record and idempotency_record.booking_id:
            existing_booking = db.get(Booking, idempotency_record.booking_id)
            if existing_booking and existing_booking.status in _ACTIVE_BOOKING_STATUSES:
                logger.info("Idempotent retry detected - returning existing booking", extra={"correlation_id": correlation_id})
                increment("booking_idempotent_retry_total")
                return existing_booking
            if existing_booking and existing_booking.status in ["CANCELLED", "REFUNDED"]:
                logger.info("Previous booking closed - allowing rebooking", extra={"correlation_id": correlation_id})
                idempotency_record.booking_id = None
                db.flush()

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
                    if existing_booking and existing_booking.status in _ACTIVE_BOOKING_STATUSES:
                        increment("booking_idempotent_retry_total")
                        return existing_booking

        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).with_for_update().one()

            if str(ride.driver_id) == str(passenger_id):
                increment("booking_failure_total")
                raise ValueError("Drivers cannot book their own ride")

            if ride.status != RideStatus.SCHEDULED:
                increment("booking_failure_total")
                raise ValueError("Ride is no longer open for new bookings")

            existing_booking = (
                db.query(Booking)
                .filter(
                    Booking.ride_id == ride_id,
                    Booking.passenger_id == passenger_id,
                    Booking.status.in_(_ACTIVE_BOOKING_STATUSES),
                )
                .first()
            )
            if existing_booking:
                increment("booking_failure_total")
                raise ValueError("You already have an active booking for this ride")

            if ride.departure_time:
                now = datetime.now(timezone.utc)
                dept = RideService._normalize_dt(ride.departure_time)
                if dept and dept < now:
                    increment("booking_failure_total")
                    raise ValueError("Cannot book a ride that has already departed")

                try:
                    RideService._check_overlapping_rides(db, passenger_id, ride.departure_time)
                except ValueError as exc:
                    increment("booking_failure_total")
                    raise ValueError(str(exc))

            closed_booking = (
                db.query(Booking)
                .filter(
                    Booking.ride_id == ride_id,
                    Booking.passenger_id == passenger_id,
                    Booking.status.in_(["CANCELLED", "REFUNDED"]),
                )
                .first()
            )

            if ride.available_seats < seats_requested:
                increment("booking_failure_total")
                raise ValueError("Not enough seats available")

            ride.available_seats -= seats_requested

            if closed_booking:
                booking = closed_booking
                booking.status = "PENDING_PAYMENT"
                booking.trip_status = BookingTripStatus.BOOKED
                booking.seats_booked = seats_requested
                booking.boarded_seats = 0
                booking.passenger_ready_at = None
                booking.boarded_at = None
                booking.passenger_boarding_confirmed_at = None
                booking.settled_amount_paise = 0
                booking.refunded_amount_paise = 0
                booking.razorpay_order_id = None
                booking.razorpay_payment_id = None
                booking.razorpay_transfer_id = None
            else:
                booking = Booking(
                    id=uuid4(),
                    ride_id=ride_id,
                    passenger_id=passenger_id,
                    seats_booked=seats_requested,
                    status="PENDING_PAYMENT",
                    trip_status=BookingTripStatus.BOOKED,
                )
                db.add(booking)

            db.flush()
            idempotency_record.booking_id = booking.id

            BookingService._queue_event(
                db,
                "booking.pending",
                {
                    "booking_id": str(booking.id),
                    "ride_id": str(booking.ride_id),
                    "passenger_id": str(booking.passenger_id),
                    "correlation_id": correlation_id,
                    "reactivated": bool(closed_booking),
                },
            )

            db.commit()
            from app.common.redis import invalidate_rides_cache

            invalidate_rides_cache()
            increment("booking_success_total")
            if closed_booking:
                increment("booking_reactivated_total")
            return booking

        except Exception:
            db.rollback()
            increment("booking_failure_total")
            logger.exception("Booking transaction failed", extra={"correlation_id": correlation_id})
            raise

    @staticmethod
    def mark_ready(
        db: Session,
        *,
        booking_id: str,
        passenger_id: str,
        correlation_id: str,
    ) -> Booking:
        booking, ride = BookingService._get_booking_for_passenger(
            db,
            booking_id=booking_id,
            passenger_id=passenger_id,
            with_lock=True,
        )
        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(ride)

        if ride.status != RideStatus.STARTED:
            raise ValueError("Ride has not started yet")
        if booking.status not in ["PAID_HELD", "CONFIRMED"]:
            raise ValueError("Only paid bookings can be marked ready")
        if booking.trip_status == BookingTripStatus.READY_AT_PICKUP:
            return booking
        if booking.trip_status not in [BookingTripStatus.BOOKED, BookingTripStatus.READY_AT_PICKUP]:
            raise ValueError("Booking is no longer eligible for pickup check-in")

        booking.trip_status = BookingTripStatus.READY_AT_PICKUP
        booking.passenger_ready_at = datetime.now(timezone.utc)
        BookingService._queue_event(
            db,
            "booking.ready_at_pickup",
            {
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "correlation_id": correlation_id,
            },
        )
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def board_booking(
        db: Session,
        *,
        booking_id: str,
        driver_id: str,
        boarded_seats: int,
        correlation_id: str,
    ) -> Booking:
        booking, ride = BookingService._get_booking_for_driver(
            db,
            booking_id=booking_id,
            driver_id=driver_id,
            with_lock=True,
        )
        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(ride)

        if ride.status != RideStatus.STARTED:
            raise ValueError("Ride must be started before passengers can board")
        if booking.status not in ["PAID_HELD", "CONFIRMED"]:
            raise ValueError("Only paid bookings can be boarded")
        if booking.trip_status not in [BookingTripStatus.READY_AT_PICKUP, BookingTripStatus.BOARDED]:
            raise ValueError("Passenger must mark ready before boarding")
        if boarded_seats < 1 or boarded_seats > booking.seats_booked:
            raise ValueError("Boarded seats must be between 1 and the booked seat count")

        booking.boarded_seats = boarded_seats
        booking.boarded_at = datetime.now(timezone.utc)
        booking.trip_status = BookingTripStatus.BOARDED
        BookingService._queue_event(
            db,
            "booking.boarded",
            {
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "boarded_seats": boarded_seats,
                "correlation_id": correlation_id,
            },
        )
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def confirm_boarding(
        db: Session,
        *,
        booking_id: str,
        passenger_id: str,
        correlation_id: str,
    ) -> Booking:
        booking, ride = BookingService._get_booking_for_passenger(
            db,
            booking_id=booking_id,
            passenger_id=passenger_id,
            with_lock=True,
        )
        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(ride)

        if booking.trip_status not in [BookingTripStatus.BOARDED, BookingTripStatus.DROPPED]:
            raise ValueError("Driver must mark you as boarded first")
        if booking.passenger_boarding_confirmed_at:
            return booking

        booking.passenger_boarding_confirmed_at = datetime.now(timezone.utc)
        BookingService._queue_event(
            db,
            "booking.boarding_confirmed",
            {
                "booking_id": str(booking.id),
                "ride_id": str(booking.ride_id),
                "passenger_id": str(booking.passenger_id),
                "correlation_id": correlation_id,
            },
        )
        db.commit()
        db.refresh(booking)
        return booking

    @staticmethod
    def get_booking_status(db: Session, *, ride_id: str, passenger_id: str) -> dict:
        booking = (
            db.query(Booking)
            .filter(Booking.ride_id == ride_id, Booking.passenger_id == passenger_id)
            .order_by(Booking.created_at.desc())
            .first()
        )
        if not booking:
            return {
                "has_booking": False,
                "booking_id": None,
                "status": None,
                "trip_status": None,
                "boarded_seats": 0,
                "passenger_ready_at": None,
                "passenger_boarding_confirmed_at": None,
                "can_mark_ready": False,
                "can_confirm_boarding": False,
                "can_cancel": False,
            }

        ride = db.query(Ride).filter(Ride.id == booking.ride_id).first()
        if ride:
            RideService.reconcile_overdue_ride(db, ride)
            db.refresh(booking)
            db.refresh(ride)

        has_booking = booking.status != "CANCELLED"
        return {
            "has_booking": has_booking,
            "booking_id": booking.id if has_booking else None,
            "status": booking.status if has_booking else None,
            "trip_status": booking.trip_status.value if has_booking else None,
            "boarded_seats": booking.boarded_seats if has_booking else 0,
            "passenger_ready_at": booking.passenger_ready_at if has_booking else None,
            "passenger_boarding_confirmed_at": booking.passenger_boarding_confirmed_at if has_booking else None,
            "can_mark_ready": bool(
                has_booking
                and ride
                and ride.status == RideStatus.STARTED
                and booking.status in ["PAID_HELD", "CONFIRMED"]
                and booking.trip_status in [BookingTripStatus.BOOKED, BookingTripStatus.READY_AT_PICKUP]
            ),
            "can_confirm_boarding": bool(
                has_booking
                and booking.trip_status in [BookingTripStatus.BOARDED, BookingTripStatus.DROPPED]
                and booking.passenger_boarding_confirmed_at is None
            ),
            "can_cancel": bool(
                has_booking
                and ride
                and ride.status == RideStatus.SCHEDULED
                and booking.status in _ACTIVE_BOOKING_STATUSES
            ),
        }
