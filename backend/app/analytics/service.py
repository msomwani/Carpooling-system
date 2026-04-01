from datetime import datetime, timedelta, UTC
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.bookings.models import Booking
from app.rides.models import Ride, RideStatus

class AnalyticsService:

    @staticmethod
    def get_overview(db: Session, *, days: int = 30):
        start_time = datetime.now(UTC) - timedelta(days=days)

        total_bookings = (
            db.query(func.count(Booking.id))
            .filter(Booking.created_at >= start_time)
            .scalar()
        ) or 0

        cancelled_bookings = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.created_at >= start_time,
                Booking.status == "CANCELLED",
            )
            .scalar()
        ) or 0

        cancellation_rate = (cancelled_bookings / total_bookings) if total_bookings else 0.0

        total_seats = (
            db.query(func.coalesce(func.sum(Ride.total_seats), 0))
            .filter(Ride.departure_time >= start_time)
            .scalar()
        ) or 0

        booked_seats = (
            db.query(func.coalesce(func.sum(Booking.seats_booked), 0))
            .join(Ride, Ride.id == Booking.ride_id)
            .filter(
                Ride.departure_time >= start_time,
                Booking.status == "CONFIRMED",
            )
            .scalar()
        ) or 0

        seat_utilization = (booked_seats / total_seats) if total_seats else 0.0

        route_rows = (
            db.query(
                Ride.source.label("source"),
                Ride.destination.label("destination"),
                func.count(Booking.id).label("bookings"),
            )
            .join(Booking, Booking.ride_id == Ride.id)
            .filter(
                Booking.status == "CONFIRMED",
                Ride.departure_time >= start_time,
            )
            .group_by(Ride.source, Ride.destination)
            .order_by(func.count(Booking.id).desc())
            .limit(5)
            .all()
        )

        popular_routes = [
            {
                "source": row.source,
                "destination": row.destination,
                "bookings": int(row.bookings),
            }
            for row in route_rows
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
        active_statuses = ["CONFIRMED", "PAID_HELD"]

        stats_row = (
            db.query(
                func.coalesce(
                    func.sum(case((Booking.status.in_(active_statuses), 1), else_=0)),
                    0,
                ).label("total_bookings"),
                func.coalesce(
                    func.sum(case((Booking.status == "CANCELLED", 1), else_=0)),
                    0,
                ).label("cancelled_bookings"),
                func.coalesce(
                    func.sum(
                        case((Booking.status.in_(active_statuses), Booking.seats_booked), else_=0)
                    ),
                    0,
                ).label("seats_booked"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Booking.status.in_(active_statuses),
                                Booking.seats_booked * Ride.price_per_seat,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_spend_inr"),
            )
            .join(Ride, Ride.id == Booking.ride_id)
            .filter(
                Booking.passenger_id == user_id,
            )
            .one()
        )

        return {
            "role": "passenger",
            "window": "lifetime",
            "stats": {
                "total_bookings": int(stats_row.total_bookings or 0),
                "cancelled_bookings": int(stats_row.cancelled_bookings or 0),
                "seats_booked": int(stats_row.seats_booked or 0),
                "total_spend_inr": int(stats_row.total_spend_inr or 0),
            },
        }

    @staticmethod
    def _get_driver_analytics(db: Session, *, user_id: str):
        AnalyticsService._sync_overdue_driver_rides(db, user_id=user_id)

        active_booking_statuses = ["CONFIRMED", "PAID_HELD"]

        stats_row = (
            db.query(
                func.count(func.distinct(Ride.id)).label("rides_created"),
                func.count(
                    func.distinct(
                        case((Ride.status == RideStatus.COMPLETED, Ride.id), else_=None)
                    )
                ).label("rides_completed"),
                func.coalesce(
                    func.sum(
                        case((Booking.status.in_(active_booking_statuses), Booking.seats_booked), else_=0)
                    ),
                    0,
                ).label("seats_shared"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Booking.status.in_(active_booking_statuses),
                                Booking.seats_booked * Ride.price_per_seat,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("gross_earnings_inr"),
            )
            .outerjoin(Booking, Booking.ride_id == Ride.id)
            .filter(Ride.driver_id == user_id)
            .one()
        )

        return {
            "role": "driver",
            "window": "lifetime",
            "stats": {
                "rides_created": int(stats_row.rides_created or 0),
                "rides_completed": int(stats_row.rides_completed or 0),
                "seats_shared": int(stats_row.seats_shared or 0),
                "gross_earnings_inr": int(stats_row.gross_earnings_inr or 0),
            },
        }

    @staticmethod
    def _sync_overdue_driver_rides(db: Session, *, user_id: str):
        from app.common.redis import invalidate_rides_cache
        from app.payments.service import PaymentService

        now = datetime.now(UTC)
        overdue_rides = (
            db.query(Ride)
            .filter(
                Ride.driver_id == user_id,
                Ride.status == RideStatus.ACTIVE,
                Ride.departure_time < now,
            )
            .all()
        )

        if not overdue_rides:
            return

        overdue_ride_ids = [ride.id for ride in overdue_rides]
        held_bookings = (
            db.query(Booking)
            .filter(
                Booking.ride_id.in_(overdue_ride_ids),
                Booking.status == "PAID_HELD",
            )
            .all()
        )

        payment_svc = PaymentService() if held_bookings else None

        for booking in held_bookings:
            if booking.razorpay_transfer_id and payment_svc is not None:
                try:
                    payment_svc.release_transfer(booking.razorpay_transfer_id)
                except Exception as e:
                    print(f"ERROR: Failed to release transfer {booking.razorpay_transfer_id}: {str(e)}")
            booking.status = "CONFIRMED"

        for ride in overdue_rides:
            ride.status = RideStatus.COMPLETED

        db.commit()
        invalidate_rides_cache()
