from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.rides.models import Ride
from app.bookings.models import Booking
from app.bookings.idempotency_model import BookingIdempotency


class BookingService:

    @staticmethod
    def create_booking(
        db: Session,
        *,
        ride_id,
        passenger_id,
        seats_requested: int,
        idempotency_key: str
    ):
        # 1️⃣ Check idempotency
        existing = db.query(BookingIdempotency).filter(
            BookingIdempotency.idempotency_key == idempotency_key
        ).first()

        if existing and existing.booking_id:
            booking = db.query(Booking).get(existing.booking_id)
            return booking

        if not existing:
            existing = BookingIdempotency(
                idempotency_key=idempotency_key
            )
            db.add(existing)
            db.flush()

        try:
            # 2️⃣ Lock the ride row
            ride = db.query(Ride).filter(
                Ride.id == ride_id
            ).with_for_update().one()

            # 3️⃣ Validate seats
            if ride.available_seats < seats_requested:
                raise ValueError("Not enough seats available")

            # 4️⃣ Update seats
            ride.available_seats -= seats_requested

            # 5️⃣ Create booking
            booking = Booking(
                ride_id=ride_id,
                passenger_id=passenger_id,
                seats_booked=seats_requested,
                status="CONFIRMED"
            )
            db.add(booking)
            db.flush()

            # 6️⃣ Link idempotency record
            existing.booking_id = booking.id

            # 7️⃣ Commit transaction
            db.commit()

            # 8️⃣ Kafka event would be published here (post-commit)

            return booking

        except Exception:
            db.rollback()
            raise
