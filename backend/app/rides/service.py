import json
import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.bookings.models import Booking, BookingTripStatus
from app.common.redis import redis_client
from app.outbox.models import OutboxEvent
from app.rides.models import Ride, RideCompletionSource, RideStatus
from app.rides.schemas import RideManifestBookingResponse, RideResponse
from app.users.models import User

# Earth radius in kilometres (mean)
_EARTH_RADIUS_KM = 6371.0
_START_WINDOW_BEFORE = timedelta(minutes=30)
_START_WINDOW_AFTER = timedelta(minutes=60)
_AUTO_COMPLETE_AFTER = timedelta(hours=6)
_START_PROXIMITY_METERS = 300.0
_COMPLETE_PROXIMITY_METERS = 500.0

# Predefined locations for "Smart Search" mapping
COMMON_LOCATIONS = {
    "tandalja": {"lat": 22.2890, "lng": 73.1520},
    "airport": {"lat": 22.3275, "lng": 73.2165},
    "amit nagar": {"lat": 22.3215, "lng": 73.2030},
    "golden chowdi": {"lat": 22.3395, "lng": 73.2201},
    "jarod": {"lat": 22.4285, "lng": 73.3850},
    "nimeta": {"lat": 22.3850, "lng": 73.3500},
    "halol": {"lat": 22.4980, "lng": 73.4735},
    "vuda": {"lat": 22.3200, "lng": 73.2100},
    "sayajigunj": {"lat": 22.3100, "lng": 73.1850},
    "station": {"lat": 22.3106, "lng": 73.1812},
    "central bus": {"lat": 22.3106, "lng": 73.1812},
    "pavagadh": {"lat": 22.5035, "lng": 73.4852},
}

logger = logging.getLogger(__name__)


class RideService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_dt(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _queue_event(db: Session, event_type: str, payload: dict):
        db.add(OutboxEvent(event_type=event_type, payload=payload))

    @staticmethod
    def _lock_bookings_for_ride(
        db: Session,
        *,
        ride_id,
        statuses: tuple[str, ...],
    ) -> list[Booking]:
        return (
            db.query(Booking)
            .filter(Booking.ride_id == ride_id, Booking.status.in_(statuses))
            .order_by(Booking.created_at.asc(), Booking.id.asc())
            .with_for_update()
            .all()
        )

    @staticmethod
    def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        hav = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        )
        return 2 * _EARTH_RADIUS_KM * 1000 * math.asin(math.sqrt(hav))

    @staticmethod
    def _ensure_ride_point(ride: Ride, *, field_prefix: str):
        lat = getattr(ride, f"{field_prefix}_lat")
        lng = getattr(ride, f"{field_prefix}_lng")
        if lat is None or lng is None:
            raise ValueError(f"Ride {field_prefix} coordinates are required for verification")
        return lat, lng

    @staticmethod
    def _ensure_near_point(
        ride: Ride,
        *,
        field_prefix: str,
        lat: float,
        lng: float,
        max_distance_meters: float,
        message: str,
    ):
        ride_lat, ride_lng = RideService._ensure_ride_point(ride, field_prefix=field_prefix)
        distance = RideService._distance_meters(lat, lng, ride_lat, ride_lng)
        if distance > max_distance_meters:
            raise ValueError(message)

    @staticmethod
    def _serialize_route_geometry(db: Session, ride: Ride):
        if not ride.route_geometry:
            return
        try:
            from geoalchemy2 import functions as ga_func

            wkt = db.query(ga_func.ST_AsText(Ride.route_geometry)).filter(Ride.id == ride.id).scalar()
            if wkt:
                ride.route_geometry = wkt
        except Exception:
            pass

    @staticmethod
    def _settle_started_ride(
        db: Session,
        *,
        ride: Ride,
        correlation_id: str | None = None,
    ):
        from app.payments.service import PaymentService

        bookings = RideService._lock_bookings_for_ride(
            db,
            ride_id=ride.id,
            statuses=("PAID_HELD",),
        )
        payment_svc = PaymentService() if bookings else None
        amount_per_seat_paise = int(ride.price_per_seat * 100)
        driver = db.query(User).filter(User.id == ride.driver_id).first()
        account_id = (driver.razorpay_account_id if driver else None) or "acc_test_dummy_123"

        for booking in bookings:
            boarded_seats = max(0, min(booking.boarded_seats or 0, booking.seats_booked))
            unboarded_seats = max(booking.seats_booked - boarded_seats, 0)
            settled_amount = boarded_seats * amount_per_seat_paise
            refund_amount = unboarded_seats * amount_per_seat_paise

            if boarded_seats > 0:
                transfer_id = booking.razorpay_transfer_id
                if booking.razorpay_payment_id and payment_svc is not None:
                    if not transfer_id:
                        transfer_response = payment_svc.create_transfer(
                            payment_id=booking.razorpay_payment_id,
                            account_id=account_id,
                            amount_in_paise=settled_amount,
                            on_hold=True,
                        )
                        transfer_id = (
                            transfer_response["items"][0]["id"]
                            if "items" in transfer_response and transfer_response["items"]
                            else None
                        )
                        if not transfer_id:
                            raise RuntimeError(f"Settlement transfer could not be created for booking {booking.id}")
                        booking.razorpay_transfer_id = transfer_id

                    if refund_amount > 0:
                        payment_svc.refund_payment(booking.razorpay_payment_id, refund_amount)

                    payment_svc.release_transfer(transfer_id)
                    booking.settled_amount_paise = settled_amount
                    booking.refunded_amount_paise = refund_amount
                else:
                    logger.warning(
                        "Skipping external settlement for booking %s because no payment id is attached.",
                        booking.id,
                    )
                    booking.settled_amount_paise = 0
                    booking.refunded_amount_paise = 0

                booking.status = "CONFIRMED"
                booking.trip_status = BookingTripStatus.DROPPED
                RideService._queue_event(
                    db,
                    "booking.settled",
                    {
                        "booking_id": str(booking.id),
                        "ride_id": str(ride.id),
                        "passenger_id": str(booking.passenger_id),
                        "boarded_seats": boarded_seats,
                        "refunded_amount_paise": booking.refunded_amount_paise,
                        "settled_amount_paise": booking.settled_amount_paise,
                        "correlation_id": correlation_id,
                    },
                )
                continue

            refund_total = booking.seats_booked * amount_per_seat_paise
            if booking.razorpay_payment_id and payment_svc is not None:
                payment_svc.refund_payment(booking.razorpay_payment_id, refund_total)
                booking.refunded_amount_paise = refund_total
            else:
                logger.warning(
                    "Skipping external refund for booking %s because no payment id is attached.",
                    booking.id,
                )
                booking.refunded_amount_paise = 0

            booking.settled_amount_paise = 0
            booking.trip_status = BookingTripStatus.NO_SHOW
            booking.status = "REFUNDED"
            RideService._queue_event(
                db,
                "booking.refunded",
                {
                    "booking_id": str(booking.id),
                    "ride_id": str(ride.id),
                    "passenger_id": str(booking.passenger_id),
                    "reason": "NO_SHOW",
                    "refunded_amount_paise": booking.refunded_amount_paise,
                    "correlation_id": correlation_id,
                },
            )

    @staticmethod
    def _refund_scheduled_ride_bookings(
        db: Session,
        *,
        ride: Ride,
        reason: str,
        correlation_id: str | None = None,
    ):
        from app.payments.service import PaymentService

        payment_svc = PaymentService()
        active_bookings = RideService._lock_bookings_for_ride(
            db,
            ride_id=ride.id,
            statuses=("PENDING_PAYMENT", "PAID_HELD", "CONFIRMED"),
        )

        for booking in active_bookings:
            refund_amount = int(booking.seats_booked * ride.price_per_seat * 100)
            if booking.razorpay_payment_id:
                payment_svc.refund_payment(booking.razorpay_payment_id, refund_amount)
                booking.status = "REFUNDED"
                booking.refunded_amount_paise = refund_amount
            else:
                booking.status = "CANCELLED"
                booking.refunded_amount_paise = 0
            booking.trip_status = BookingTripStatus.BOOKED
            booking.boarded_seats = 0
            booking.passenger_ready_at = None
            booking.boarded_at = None
            booking.passenger_boarding_confirmed_at = None
            booking.settled_amount_paise = 0

            RideService._queue_event(
                db,
                "booking.refunded",
                {
                    "booking_id": str(booking.id),
                    "ride_id": str(ride.id),
                    "passenger_id": str(booking.passenger_id),
                    "reason": reason,
                    "refunded_amount_paise": refund_amount if booking.razorpay_payment_id else 0,
                    "correlation_id": correlation_id,
                },
            )

    @staticmethod
    def _reconcile_locked_ride(db: Session, ride: Ride) -> bool:
        departure_time = RideService._normalize_dt(ride.departure_time)
        if departure_time is None:
            return False

        now = RideService._now()
        changed = False

        if ride.status == RideStatus.SCHEDULED and now > departure_time + _START_WINDOW_AFTER:
            RideService._refund_scheduled_ride_bookings(db, ride=ride, reason="MISSED_START")
            ride.status = RideStatus.MISSED_START
            RideService._queue_event(
                db,
                "ride.missed_start",
                {"ride_id": str(ride.id), "driver_id": str(ride.driver_id)},
            )
            changed = True

        elif ride.status == RideStatus.STARTED and now > departure_time + _AUTO_COMPLETE_AFTER:
            ride.actual_complete_lat = ride.destination_lat
            ride.actual_complete_lng = ride.destination_lng
            ride.actual_completed_at = now
            ride.completed_by = RideCompletionSource.SYSTEM
            ride.status = RideStatus.COMPLETED
            RideService._settle_started_ride(db, ride=ride)
            RideService._queue_event(
                db,
                "ride.completed",
                {
                    "ride_id": str(ride.id),
                    "driver_id": str(ride.driver_id),
                    "completed_by": RideCompletionSource.SYSTEM.value,
                },
            )
            changed = True

        if changed:
            db.commit()
            db.refresh(ride)
            from app.common.redis import invalidate_rides_cache

            invalidate_rides_cache()
        return changed

    @staticmethod
    def reconcile_overdue_ride(db: Session, ride: Ride) -> bool:
        locked_ride = db.query(Ride).filter(Ride.id == ride.id).with_for_update().first()
        if not locked_ride:
            return False
        return RideService._reconcile_locked_ride(db, locked_ride)

    @staticmethod
    def _check_overlapping_rides(db: Session, user_id: str, new_departure: datetime):
        window_start = new_departure - timedelta(hours=2)
        window_end = new_departure + timedelta(hours=2)

        overlapping_driving = (
            db.query(Ride)
            .filter(
                Ride.driver_id == user_id,
                Ride.status.in_([RideStatus.SCHEDULED, RideStatus.STARTED]),
                Ride.departure_time >= window_start,
                Ride.departure_time <= window_end,
            )
            .first()
        )
        if overlapping_driving:
            raise ValueError("You are already scheduled to drive another ride within 2 hours of this time.")

        overlapping_riding = (
            db.query(Booking)
            .join(Ride, Ride.id == Booking.ride_id)
            .filter(
                Booking.passenger_id == user_id,
                Booking.status.in_(["PAID_HELD", "PENDING_PAYMENT"]),
                Ride.status.in_([RideStatus.SCHEDULED, RideStatus.STARTED]),
                Ride.departure_time >= window_start,
                Ride.departure_time <= window_end,
            )
            .first()
        )
        if overlapping_riding:
            raise ValueError("You already have a booking for another ride within 2 hours of this time.")

    @staticmethod
    def create_ride(
        db: Session,
        *,
        driver_id: str,
        source: str,
        source_lat: float | None = None,
        source_lng: float | None = None,
        destination: str,
        destination_lat: float | None = None,
        destination_lng: float | None = None,
        departure_time=None,
        total_seats: int,
        price_per_seat: int = 0,
        vehicle_id: str | None = None,
        route_geometry: str | None = None,
    ) -> Ride:
        from app.vehicles.models import Vehicle

        if vehicle_id:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                raise ValueError("Vehicle not found")
            if str(vehicle.owner_id) != str(driver_id):
                raise PermissionError("You do not own this vehicle")

        if total_seats <= 0:
            raise ValueError("Total seats must be greater than zero")

        if departure_time:
            now = RideService._now()
            dept = RideService._normalize_dt(departure_time)
            if dept and dept < now:
                raise ValueError("Cannot create a ride in the past")
            RideService._check_overlapping_rides(db, driver_id, departure_time)

        ride = Ride(
            driver_id=driver_id,
            source=source,
            source_lat=source_lat,
            source_lng=source_lng,
            source_location=f"POINT({source_lng} {source_lat})" if source_lat is not None else None,
            destination=destination,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            destination_location=f"POINT({destination_lng} {destination_lat})" if destination_lat is not None else None,
            departure_time=departure_time,
            total_seats=total_seats,
            available_seats=total_seats,
            price_per_seat=price_per_seat,
            vehicle_id=vehicle_id,
            route_geometry=route_geometry,
            status=RideStatus.SCHEDULED,
        )

        db.add(ride)
        db.flush()

        RideService._queue_event(
            db,
            "ride.created",
            {"ride_id": str(ride.id), "driver_id": str(ride.driver_id)},
        )
        db.commit()
        db.refresh(ride)

        from app.common.redis import invalidate_rides_cache

        invalidate_rides_cache()
        return ride

    @staticmethod
    def _get_ride_owned_by(
        db: Session,
        ride_id: str,
        driver_id: str,
        *,
        allowed_statuses: tuple[RideStatus, ...] | None = None,
        with_lock: bool = False,
    ) -> Ride:
        query = db.query(Ride).filter(Ride.id == ride_id)
        if with_lock:
            query = query.with_for_update()
        ride = query.first()
        if not ride:
            raise ValueError("Ride not found")
        if str(ride.driver_id) != str(driver_id):
            raise PermissionError("You are not the driver of this ride")
        if allowed_statuses and ride.status not in allowed_statuses:
            allowed = ", ".join(status.value for status in allowed_statuses)
            raise ValueError(f"Ride must be in one of: {allowed}")
        return ride

    @staticmethod
    def get_ride_by_id(db: Session, ride_id: str):
        from app.vehicles.models import Vehicle

        ride = db.query(Ride).filter(Ride.id == ride_id).first()
        if not ride:
            return None

        RideService.reconcile_overdue_ride(db, ride)
        db.refresh(ride)
        RideService._serialize_route_geometry(db, ride)

        driver = db.query(User).filter(User.id == ride.driver_id).first()
        vehicle = None
        if ride.vehicle_id:
            vehicle = db.query(Vehicle).filter(Vehicle.id == ride.vehicle_id).first()

        return {
            "ride": ride,
            "driver_name": driver.name if driver else "Unknown",
            "vehicle_make": vehicle.make if vehicle else None,
            "vehicle_model": vehicle.model if vehicle else None,
            "vehicle_color": vehicle.color if vehicle else None,
            "vehicle_license_plate": vehicle.license_plate if vehicle else None,
        }

    @staticmethod
    def get_driver_rides(db: Session, driver_id: str):
        rides = (
            db.query(Ride)
            .filter(Ride.driver_id == driver_id)
            .order_by(Ride.departure_time.desc().nulls_last())
            .all()
        )
        for ride in rides:
            RideService.reconcile_overdue_ride(db, ride)
            db.refresh(ride)
            RideService._serialize_route_geometry(db, ride)
        return rides

    @staticmethod
    def get_ride_manifest(db: Session, *, ride_id: str, driver_id: str) -> list[RideManifestBookingResponse]:
        ride = RideService._get_ride_owned_by(db, ride_id, driver_id)
        RideService.reconcile_overdue_ride(db, ride)

        rows = (
            db.query(Booking, User)
            .join(User, User.id == Booking.passenger_id)
            .filter(
                Booking.ride_id == ride_id,
                Booking.status.in_(["PAID_HELD", "CONFIRMED", "REFUNDED"]),
            )
            .order_by(Booking.created_at.asc())
            .all()
        )

        return [
            RideManifestBookingResponse(
                booking_id=booking.id,
                passenger_name=user.name,
                seats_booked=booking.seats_booked,
                boarded_seats=booking.boarded_seats,
                trip_status=booking.trip_status.value,
                passenger_ready_at=booking.passenger_ready_at,
                passenger_boarding_confirmed_at=booking.passenger_boarding_confirmed_at,
                payment_status=booking.status,
            )
            for booking, user in rows
        ]

    @staticmethod
    def start_ride(
        db: Session,
        *,
        ride_id: str,
        driver_id: str,
        lat: float,
        lng: float,
        correlation_id: str | None = None,
    ) -> Ride:
        ride = RideService._get_ride_owned_by(
            db,
            ride_id,
            driver_id,
            allowed_statuses=(RideStatus.SCHEDULED,),
            with_lock=True,
        )

        departure_time = RideService._normalize_dt(ride.departure_time)
        now = RideService._now()
        if departure_time is None:
            raise ValueError("Ride departure time is required")
        if now < departure_time - _START_WINDOW_BEFORE or now > departure_time + _START_WINDOW_AFTER:
            raise ValueError("Ride can only be started from 30 minutes before to 60 minutes after departure time")

        RideService._ensure_near_point(
            ride,
            field_prefix="source",
            lat=lat,
            lng=lng,
            max_distance_meters=_START_PROXIMITY_METERS,
            message="You must be near the ride pickup point to start the ride",
        )

        ride.status = RideStatus.STARTED
        ride.actual_started_at = now
        ride.actual_start_lat = lat
        ride.actual_start_lng = lng
        RideService._queue_event(
            db,
            "ride.started",
            {
                "ride_id": str(ride.id),
                "driver_id": str(ride.driver_id),
                "correlation_id": correlation_id,
            },
        )

        db.commit()
        db.refresh(ride)
        from app.common.redis import invalidate_rides_cache

        invalidate_rides_cache()
        return ride

    @staticmethod
    def complete_ride(
        db: Session,
        *,
        ride_id: str,
        driver_id: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        correlation_id: str | None = None,
        completed_by: RideCompletionSource = RideCompletionSource.DRIVER,
        require_driver: bool = True,
        skip_location_check: bool = False,
    ) -> Ride:
        query = db.query(Ride).filter(Ride.id == ride_id).with_for_update()
        ride = query.first()
        if not ride:
            raise ValueError("Ride not found")
        if require_driver:
            if str(ride.driver_id) != str(driver_id):
                raise PermissionError("You are not the driver of this ride")
        if ride.status != RideStatus.STARTED:
            raise ValueError("Ride must be started before it can be completed")

        if not skip_location_check:
            if lat is None or lng is None:
                raise ValueError("Driver location is required to complete the ride")
            RideService._ensure_near_point(
                ride,
                field_prefix="destination",
                lat=lat,
                lng=lng,
                max_distance_meters=_COMPLETE_PROXIMITY_METERS,
                message="You must be near the destination to complete the ride",
            )

        ride.status = RideStatus.COMPLETED
        ride.actual_completed_at = RideService._now()
        ride.actual_complete_lat = lat
        ride.actual_complete_lng = lng
        ride.completed_by = completed_by

        RideService._settle_started_ride(db, ride=ride, correlation_id=correlation_id)
        RideService._queue_event(
            db,
            "ride.completed",
            {
                "ride_id": str(ride.id),
                "driver_id": str(ride.driver_id),
                "completed_by": completed_by.value,
                "correlation_id": correlation_id,
            },
        )

        db.commit()
        db.refresh(ride)
        from app.common.redis import invalidate_rides_cache

        invalidate_rides_cache()
        return ride

    @staticmethod
    def cancel_ride(db: Session, *, ride_id: str, driver_id: str, correlation_id: str = None) -> Ride:
        ride = RideService._get_ride_owned_by(
            db,
            ride_id,
            driver_id,
            allowed_statuses=(RideStatus.SCHEDULED,),
            with_lock=True,
        )
        now = RideService._now()

        active_bookings = RideService._lock_bookings_for_ride(
            db,
            ride_id=ride_id,
            statuses=("PENDING_PAYMENT", "CONFIRMED", "PAID_HELD"),
        )
        has_passengers = len(active_bookings) > 0

        if ride.departure_time:
            dept = RideService._normalize_dt(ride.departure_time)
            time_until_departure = dept - now
            is_late_cancellation = time_until_departure < timedelta(hours=1.5)

            if has_passengers and is_late_cancellation:
                raise ValueError("Cannot cancel a ride with confirmed passengers within 1.5 hours of departure.")

            RideService._queue_event(
                db,
                "ride.cancelled",
                {
                    "ride_id": str(ride.id),
                    "driver_id": str(ride.driver_id),
                    "has_passengers": has_passengers,
                    "is_late": is_late_cancellation,
                    "correlation_id": correlation_id,
                },
            )

        from app.payments.service import PaymentService

        payment_svc = PaymentService()
        for booking in active_bookings:
            if booking.razorpay_payment_id:
                refund_amount = int(booking.seats_booked * ride.price_per_seat * 100)
                payment_svc.refund_payment(booking.razorpay_payment_id, refund_amount)
                booking.refunded_amount_paise = refund_amount
            booking.status = "CANCELLED"
            RideService._queue_event(
                db,
                "booking.cancelled_by_driver",
                {
                    "booking_id": str(booking.id),
                    "ride_id": str(ride.id),
                    "passenger_id": str(booking.passenger_id),
                    "correlation_id": correlation_id,
                },
            )

        ride.status = RideStatus.CANCELLED
        db.commit()
        db.refresh(ride)

        from app.common.redis import invalidate_rides_cache

        invalidate_rides_cache()
        return ride

    @staticmethod
    def search_nearby(
        db: Session,
        *,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        role: str = "source",
    ) -> list[Ride]:
        radius_m = radius_km * 1000
        search_point = f"SRID=4326;POINT({lng} {lat})"

        if role == "path":
            return (
                db.query(Ride)
                .filter(
                    Ride.route_geometry.isnot(None),
                    Ride.available_seats > 0,
                    Ride.status == RideStatus.SCHEDULED,
                    Ride.departure_time > sa_func.now(),
                    sa_func.ST_DWithin(Ride.route_geometry, search_point, radius_m),
                )
                .all()
            )

        loc_col = Ride.source_location if role == "source" else Ride.destination_location

        return (
            db.query(Ride)
            .filter(
                loc_col.isnot(None),
                Ride.available_seats > 0,
                Ride.status == RideStatus.SCHEDULED,
                Ride.departure_time > sa_func.now(),
                sa_func.ST_DWithin(loc_col, search_point, radius_m),
            )
            .all()
        )

    @staticmethod
    def _geocode(name: str) -> tuple[float, float] | None:
        clean_name = name.lower().strip()
        for key, coords in COMMON_LOCATIONS.items():
            if key in clean_name:
                return coords["lat"], coords["lng"]
        return None

    @staticmethod
    def search_rides(
        db: Session,
        *,
        source: str,
        destination: str,
    ) -> list[RideResponse]:
        cache_key = f"rides:{source}:{destination}"

        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        query = db.query(Ride).filter(
            Ride.available_seats > 0,
            Ride.status == RideStatus.SCHEDULED,
            Ride.departure_time > sa_func.now(),
        )

        s_coords = RideService._geocode(source)
        d_coords = RideService._geocode(destination)

        if s_coords and d_coords:
            s_point = f"SRID=4326;POINT({s_coords[1]} {s_coords[0]})"
            d_point = f"SRID=4326;POINT({d_coords[1]} {d_coords[0]})"
            query = query.filter(
                Ride.route_geometry.isnot(None),
                sa_func.ST_DWithin(Ride.route_geometry, s_point, 5000),
                sa_func.ST_DWithin(Ride.route_geometry, d_point, 5000),
            )
        else:
            query = query.filter(
                Ride.source.ilike(f"%{source}%"),
                Ride.destination.ilike(f"%{destination}%"),
            )

        rides = query.all()
        for ride in rides:
            RideService._serialize_route_geometry(db, ride)

        result = [RideResponse.model_validate(ride) for ride in rides]
        redis_client.setex(cache_key, 60, json.dumps([ride.model_dump(mode="json") for ride in result]))
        return result
