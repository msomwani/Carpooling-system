from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.bookings.models import Booking
from app.common.db import get_db
from app.rides.models import Ride

router = APIRouter(prefix="/analytics", tags=["Analytics"])





@router.get("/overview")
def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
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

