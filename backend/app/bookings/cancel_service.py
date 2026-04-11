import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.bookings.models import Booking, BookingTripStatus
from app.outbox.models import OutboxEvent
from app.rides.models import Ride, RideStatus
from app.rides.service import RideService

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

        booking = db.query(Booking).filter(Booking.id == booking_id).first()

        if not booking:
            raise ValueError("Booking not found")

        if str(booking.passenger_id) != str(user_id):
            raise ValueError("Not authorized to cancel this booking")

        if booking.status == "CANCELLED":
            raise ValueError("Booking already cancelled")
        if booking.status == "REFUNDED":
            raise ValueError("Booking is already refunded")

        ride = (
            db.query(Ride)
            .filter(Ride.id == booking.ride_id)
            .with_for_update()
            .first()
        )

        if not ride:
            raise ValueError("Ride not found")

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
        if booking.status == "REFUNDED":
            raise ValueError("Booking is already refunded")

        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(ride)

        if ride.status != RideStatus.SCHEDULED:
            raise ValueError("Cannot cancel booking after the ride has started")

        if ride.departure_time:
            now = datetime.now(timezone.utc)
            dept = RideService._normalize_dt(ride.departure_time)
            if dept and dept < now:
                raise ValueError("Cannot cancel booking for a ride that has already departed")

        refund_amount = int(booking.seats_booked * ride.price_per_seat * 100)
        needs_refund = bool(
            booking.status in ["PAID_HELD", "CONFIRMED"]
            and booking.razorpay_payment_id
            and refund_amount > 0
        )
        razorpay_payment_id = booking.razorpay_payment_id

        ride.available_seats += booking.seats_booked

        booking.trip_status = BookingTripStatus.BOOKED
        booking.boarded_seats = 0
        booking.passenger_ready_at = None
        booking.boarded_at = None
        booking.passenger_boarding_confirmed_at = None
        booking.settled_amount_paise = 0
        booking.refunded_amount_paise = 0

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
        db.refresh(booking)

        # Invalidate Redis cache after successful cancellation
        from app.common.redis import invalidate_rides_cache

        invalidate_rides_cache()

        logger.info(
            "Cancellation committed successfully",
            extra={"correlation_id": correlation_id},
        )

        if not needs_refund:
            return booking

        from app.payments.service import PaymentService

        try:
            PaymentService().refund_payment(razorpay_payment_id, refund_amount)
        except Exception as e:
            logger.error(
                "Refund failed after local cancellation commit for payment %s: %s",
                razorpay_payment_id,
                str(e),
                extra={"correlation_id": correlation_id},
            )
            return booking

        try:
            booking = (
                db.query(Booking)
                .filter(Booking.id == booking_id)
                .with_for_update()
                .first()
            )
            if booking:
                booking.refunded_amount_paise = refund_amount
                db.add(
                    OutboxEvent(
                        event_type="booking.refunded",
                        payload={
                            "booking_id": str(booking.id),
                            "ride_id": str(booking.ride_id),
                            "passenger_id": str(booking.passenger_id),
                            "reason": "PASSENGER_CANCELLED",
                            "refunded_amount_paise": refund_amount,
                            "correlation_id": correlation_id,
                        },
                    )
                )
                db.commit()
                db.refresh(booking)
                logger.info(
                    "Refund completed for booking %s",
                    booking.id,
                    extra={"correlation_id": correlation_id},
                )
        except Exception:
            db.rollback()
            logger.exception(
                "Refund succeeded externally but local refund bookkeeping update failed for booking %s",
                booking_id,
                extra={"correlation_id": correlation_id},
            )

        return booking
