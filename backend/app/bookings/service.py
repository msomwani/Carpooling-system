from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.rides.models import Ride
from app.bookings.models import Booking
from app.bookings.idempotency_model import BookingIdempotency
from uuid import uuid4

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
        idempo = (
            db.query(BookingIdempotency)
            .filter(BookingIdempotency.idempotency_key == idempotency_key)
            .first()
        )

        if idempo and idempo.booking_id:
            return db.query(Booking).get(idempo.booking_id)

        if not idempo:
            idempo = BookingIdempotency(idempotency_key=idempotency_key)
            db.add(idempo)
            db.flush()

        try:
            # 2️⃣ Lock ride
            ride = (
                db.query(Ride)
                .filter(Ride.id == ride_id)
                .with_for_update()
                .one()
            )

            # 3️⃣ Validate seats
            if ride.available_seats < seats_requested:
                raise ValueError("Not enough seats available")

            # 4️⃣ Update seats
            ride.available_seats -= seats_requested

            # 5️⃣ Create booking
            booking = Booking(
                id=uuid4(),
                ride_id=ride_id,
                passenger_id=passenger_id,
                seats_booked=seats_requested,
                status="CONFIRMED",
            )

            db.add(booking)

            try:
                db.flush()
            except IntegrityError:
                # 🚨 Duplicate booking for same ride + passenger
                db.rollback()

                existing_booking = (
                    db.query(Booking)
                    .filter(
                        Booking.ride_id == ride_id,
                        Booking.passenger_id == passenger_id,
                    )
                    .first()
                )

                return existing_booking

            # 6️⃣ Link idempotency
            idempo.booking_id = booking.id

            # 7️⃣ Commit DB
            db.commit()

        except Exception:
            db.rollback()
            raise

        # 8️⃣ Publish Kafka AFTER commit (never break booking)
        try:
            from app.common.kafka import publish_event

            publish_event(
                topic="booking.confirmed",
                payload={
                    "booking_id": str(booking.id),
                    "ride_id": str(booking.ride_id),
                    "passenger_id": str(booking.passenger_id),
                },
            )
        except Exception as e:
            print("Kafka publish failed:", e)

        # ✅ ALWAYS return booking
        return booking
