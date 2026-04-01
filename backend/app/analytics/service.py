from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.bookings.models import Booking
from app.rides.models import Ride, RideStatus
from app.rides.service import RideService


class AnalyticsService:
    @staticmethod
    def get_overview(db: Session, *, days: int = 30):
        start_time = datetime.now(UTC) - timedelta(days=days)

        bookings = db.query(Booking).filter(Booking.created_at >= start_time).all()
        rides = db.query(Ride).filter(Ride.departure_time >= start_time).all()
        ride_map = {ride.id: ride for ride in rides}

        total_bookings = len(bookings)
        cancelled_bookings = sum(1 for booking in bookings if booking.status == "CANCELLED")
        cancellation_rate = (cancelled_bookings / total_bookings) if total_bookings else 0.0

        utilization_rides = [ride for ride in rides if ride.status in [RideStatus.STARTED, RideStatus.COMPLETED]]
        total_seats = sum(ride.total_seats for ride in utilization_rides)
        booked_seats = sum(
            booking.boarded_seats
            for booking in bookings
            if booking.status == "CONFIRMED"
            and booking.ride_id in ride_map
            and ride_map[booking.ride_id].status in [RideStatus.STARTED, RideStatus.COMPLETED]
        )
        seat_utilization = (booked_seats / total_seats) if total_seats else 0.0

        route_totals: dict[tuple[str, str], int] = {}
        for booking in bookings:
            if booking.status != "CONFIRMED":
                continue
            ride = ride_map.get(booking.ride_id)
            if not ride:
                continue
            key = (ride.source, ride.destination)
            route_totals[key] = route_totals.get(key, 0) + booking.boarded_seats

        popular_routes = [
            {"source": source, "destination": destination, "bookings": count}
            for (source, destination), count in sorted(
                route_totals.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:5]
        ]

        return {
            "window_days": days,
            "total_bookings": int(total_bookings),
            "cancellation_rate": round(cancellation_rate, 4),
            "seat_utilization": round(seat_utilization, 4),
            "popular_routes": popular_routes,
        }

    @staticmethod
    def get_personal_analytics(db: Session, *, user_id: str, role: str):
        if role == "driver":
            return AnalyticsService._get_driver_analytics(db, user_id=user_id)
        return AnalyticsService._get_passenger_analytics(db, user_id=user_id)

    @staticmethod
    def _get_passenger_analytics(db: Session, *, user_id: str):
        bookings = (
            db.query(Booking, Ride)
            .join(Ride, Ride.id == Booking.ride_id)
            .filter(Booking.passenger_id == user_id)
            .all()
        )

        total_bookings = 0
        cancelled_bookings = 0
        seats_booked = 0
        total_spend_inr = 0

        for booking, ride in bookings:
            RideService.reconcile_overdue_ride(db, ride)
            db.refresh(booking)
            db.refresh(ride)

            if booking.status in ["PAID_HELD", "CONFIRMED"]:
                total_bookings += 1
            if booking.status in ["CANCELLED", "REFUNDED"]:
                cancelled_bookings += 1

            if booking.status == "CONFIRMED":
                seats_booked += booking.boarded_seats
                total_spend_inr += int((booking.settled_amount_paise or 0) / 100)
            elif booking.status == "PAID_HELD":
                seats_booked += booking.seats_booked
                total_spend_inr += booking.seats_booked * ride.price_per_seat

        return {
            "role": "passenger",
            "window": "lifetime",
            "stats": {
                "total_bookings": total_bookings,
                "cancelled_bookings": cancelled_bookings,
                "seats_booked": seats_booked,
                "total_spend_inr": total_spend_inr,
            },
        }

    @staticmethod
    def _get_driver_analytics(db: Session, *, user_id: str):
        rides = db.query(Ride).filter(Ride.driver_id == user_id).all()
        for ride in rides:
            RideService.reconcile_overdue_ride(db, ride)
            db.refresh(ride)

        ride_ids = [ride.id for ride in rides]
        bookings = db.query(Booking).filter(Booking.ride_id.in_(ride_ids)).all() if ride_ids else []

        rides_completed = sum(1 for ride in rides if ride.status == RideStatus.COMPLETED)
        seats_shared = sum(booking.boarded_seats for booking in bookings if booking.status == "CONFIRMED")
        gross_earnings_inr = sum(int((booking.settled_amount_paise or 0) / 100) for booking in bookings if booking.status == "CONFIRMED")

        return {
            "role": "driver",
            "window": "lifetime",
            "stats": {
                "rides_created": len(rides),
                "rides_completed": rides_completed,
                "seats_shared": seats_shared,
                "gross_earnings_inr": gross_earnings_inr,
            },
        }
