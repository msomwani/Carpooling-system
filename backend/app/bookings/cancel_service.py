from sqlalchemy.orm import Session

from app.bookings.models import Booking
from app.rides.models import Ride


class CancellationService:

    @staticmethod
    def cancel_booking(db: Session, *, booking_id: str, user_id: str):
        # Lock booking row
        booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id)
            .with_for_update()
            .first()
        )

        if not booking:
            raise ValueError("Booking not found")

        # Authorization check
        if str(booking.passenger_id) != str(user_id):
            raise ValueError("Not authorized to cancel this booking")

        # Already cancelled?
        if booking.status == "CANCELLED":
            raise ValueError("Booking already cancelled")

        # Lock ride row
        ride = (
            db.query(Ride)
            .filter(Ride.id == booking.ride_id)
            .with_for_update()
            .first()
        )

        # Restore seats
        ride.available_seats += booking.seats_booked

        #  Mark cancelled
        booking.status = "CANCELLED"

        db.commit()

        # Publish compensating event AFTER commit
        try:
            from app.common.kafka import publish_event

            publish_event(
                topic="booking.cancelled",
                payload={
                    "booking_id": str(booking.id),
                    "ride_id": str(booking.ride_id),
                    "passenger_id": str(booking.passenger_id),
                },
            )
        except Exception as e:
            print("Kafka publish failed:", e)

        return booking
