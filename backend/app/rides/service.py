import json
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Float
from datetime import datetime, timezone
from app.rides.models import Ride, RideStatus
from app.rides.models import Ride, RideStatus
from app.bookings.models import Booking
from app.users.models import User
from app.common.redis import redis_client
from app.rides.schemas import RideResponse
from datetime import timedelta
from app.outbox.models import OutboxEvent

# Earth radius in kilometres (mean)
_EARTH_RADIUS_KM = 6371.0

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


class RideService:

    @staticmethod
    def _check_overlapping_rides(db: Session, user_id: str, new_departure: datetime):
        """
        Check if the user is already booked on another ride (as driver or passenger)
        within +/- 2 hours of the proposed departure time.
        """
        window_start = new_departure - timedelta(hours=2)
        window_end = new_departure + timedelta(hours=2)
        
        # Strip tzinfo for querying PostgreSQL if new_departure is aware
        # but the db might store it strangely, or keep it aware if using timezone=True
        # Safest is just to compare directly as the engine handles timezone translation at driver level


        # 1. Check if user is DRIVING an overlapping ACTIVE ride
        overlapping_driving = (
            db.query(Ride)
            .filter(
                Ride.driver_id == user_id,
                Ride.status == RideStatus.ACTIVE,
                Ride.departure_time >= window_start,
                Ride.departure_time <= window_end,
            )
            .first()
        )
        if overlapping_driving:
            raise ValueError("You are already scheduled to drive another ride within 2 hours of this time.")

        # 2. Check if user is a PASSENGER on an overlapping CONFIRMED booking
        overlapping_riding = (
            db.query(Booking)
            .join(Ride, Ride.id == Booking.ride_id)
            .filter(
                Booking.passenger_id == user_id,
                Booking.status == "CONFIRMED",
                Ride.status == RideStatus.ACTIVE,
                Ride.departure_time >= window_start,
                Ride.departure_time <= window_end,
            )
            .first()
        )
        if overlapping_riding:
            raise ValueError("You already have a confirmed booking for another ride within 2 hours of this time.")

    @staticmethod
    def sync_ride_status(db: Session, ride: Ride) -> bool:
        """
        Check if an ACTIVE ride's departure time has passed and update to COMPLETED.
        Returns True if status was changed, False otherwise.
        """
        if ride.status == RideStatus.ACTIVE and ride.departure_time:
            now = datetime.now(timezone.utc)
            dept = ride.departure_time
            if dept.tzinfo is None:
                dept = dept.replace(tzinfo=timezone.utc)
            
            if dept < now:
                ride.status = RideStatus.COMPLETED
                db.commit()
                db.refresh(ride)
                print(f"DEBUG: Synced ride {ride.id} status to COMPLETED (departure was {dept})")
                # Invalidate cache
                from app.common.redis import invalidate_rides_cache
                invalidate_rides_cache()
                return True
        return False

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
        
        # 0. Verify vehicle ownership
        if vehicle_id:
            vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                raise ValueError("Vehicle not found")
            if str(vehicle.owner_id) != str(driver_id):
                raise PermissionError("You do not own this vehicle")

        if total_seats <= 0:
            raise ValueError("Total seats must be greater than zero")

        # Validate temporal constraints
        if departure_time:
            now = datetime.now(timezone.utc)
            dept = departure_time
            if dept.tzinfo is None:
                dept = dept.replace(tzinfo=timezone.utc)
            if dept < now:
                raise ValueError("Cannot create a ride in the past")

            # Check for double-booking overlaps
            RideService._check_overlapping_rides(db, driver_id, departure_time)

        # Any authenticated user can create a ride — role is a preference, not a gate
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
            status=RideStatus.ACTIVE,
        )


        db.add(ride)
        db.flush()  # Generate UUID if not provided

        outbox_event = OutboxEvent(
            event_type="ride.created",
            payload={
                "ride_id": str(ride.id),
                "driver_id": str(ride.driver_id),
            },
        )
        db.add(outbox_event)
        db.commit()
        db.refresh(ride)

        from app.common.redis import invalidate_rides_cache
        invalidate_rides_cache()

        return ride

    @staticmethod
    def _get_ride_owned_by(db: Session, ride_id: str, driver_id: str) -> Ride:
        """Fetch an ACTIVE ride that belongs to the given driver, or raise."""
        ride = db.query(Ride).filter(Ride.id == ride_id).first()
        if not ride:
            raise ValueError("Ride not found")
        if str(ride.driver_id) != str(driver_id):
            raise PermissionError("You are not the driver of this ride")
        if ride.status != RideStatus.ACTIVE:
            raise ValueError(f"Ride is already {ride.status.value}")
        return ride

    @staticmethod
    def get_ride_by_id(db: Session, ride_id: str):
        """Fetch a specific ride by ID, including driver and vehicle details."""
        from app.vehicles.models import Vehicle
        from geoalchemy2 import functions as ga_func
        
        ride = db.query(Ride).filter(Ride.id == ride_id).first()
        if not ride:
            return None
        
        # Use a fresh query to get WKT to avoid session state issues with Geography type
        if ride.route_geometry:
            try:
                wkt = db.query(ga_func.ST_AsText(Ride.route_geometry)).filter(Ride.id == ride_id).scalar()
                if wkt:
                    ride.route_geometry = wkt
            except Exception:
                pass # Fallback to whatever's in the object (handled by schema)

        # Sync status before returning
        RideService.sync_ride_status(db, ride)
        
        # Get driver info
        driver = db.query(User).filter(User.id == ride.driver_id).first()
        
        # Get vehicle info
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
        """Fetch all rides created by the given driver, ordered by descending departure time."""
        from geoalchemy2 import functions as ga_func
        rides = (
            db.query(Ride)
            .filter(Ride.driver_id == driver_id)
            .order_by(Ride.departure_time.desc().nulls_last())
            .all()
        )
        for r in rides:
            RideService.sync_ride_status(db, r)
            if r.route_geometry:
                r.route_geometry = db.query(ga_func.ST_AsText(Ride.route_geometry)).filter(Ride.id == r.id).scalar()
        return rides

    @staticmethod
    def complete_ride(db: Session, *, ride_id: str, driver_id: str) -> Ride:
        """Mark a ride as COMPLETED. Only the owning driver can do this."""
        ride = RideService._get_ride_owned_by(db, ride_id, driver_id)
        
        if ride.departure_time:
            now = datetime.now(timezone.utc)
            dept = ride.departure_time
            if dept.tzinfo is None:
                dept = dept.replace(tzinfo=timezone.utc)
            if dept > now:
                raise ValueError("Cannot complete a ride before its departure time")
                
        ride.status = RideStatus.COMPLETED
        db.commit()
        db.refresh(ride)

        from app.common.redis import invalidate_rides_cache
        invalidate_rides_cache()

        return ride

    @staticmethod
    def cancel_ride(db: Session, *, ride_id: str, driver_id: str, correlation_id: str = None) -> Ride:
        """Cancel a ride and cascade cancellations to passengers."""
        from app.outbox.models import OutboxEvent

        ride = RideService._get_ride_owned_by(db, ride_id, driver_id)
        now = datetime.now(timezone.utc)

        # 1. Fetch all confirmed bookings for this ride
        active_bookings = (
            db.query(Booking)
            .filter(Booking.ride_id == ride_id, Booking.status == "CONFIRMED")
            .all()
        )

        has_passengers = len(active_bookings) > 0

        # 2. Check penalty logic
        if ride.departure_time:
            dept = ride.departure_time
            if dept.tzinfo is None:
                dept = dept.replace(tzinfo=timezone.utc)
            time_until_departure = dept - now
            is_late_cancellation = time_until_departure < timedelta(hours=1.5)

            if has_passengers and is_late_cancellation:
                raise ValueError("Cannot cancel a ride with confirmed passengers within 1.5 hours of departure.")
            
            # Trigger driver cancellation event
            outbox_event = OutboxEvent(
                event_type="ride.cancelled",
                payload={
                    "ride_id": str(ride.id),
                    "driver_id": str(ride.driver_id),
                    "has_passengers": has_passengers,
                    "is_late": is_late_cancellation,
                    "correlation_id": correlation_id,
                },
            )
            db.add(outbox_event)

        # 3. Cascade cancellation to passengers
        for booking in active_bookings:
            booking.status = "CANCELLED"
            # Trigger passenger refund event
            outbox_event = OutboxEvent(
                event_type="booking.cancelled_by_driver",
                payload={
                    "booking_id": str(booking.id),
                    "ride_id": str(ride.id),
                    "passenger_id": str(booking.passenger_id),
                    "correlation_id": correlation_id,
                },
            )
            db.add(outbox_event)

        # 4. Cancel the ride itself
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
        """
        Find ACTIVE rides within *radius_km* of a given (lat, lng).

        Modes (role):
        - "source"      — matches rides whose starting point is nearby.
        - "destination" — matches rides whose ending point is nearby.
        - "path"        — matches rides whose full route geometry (LineString)
                          passes within radius_km of the point. Rides without
                          a stored route_geometry are excluded.
        """
        # PostGIS expects metres; convert km → m
        radius_m = radius_km * 1000
        search_point = f"SRID=4326;POINT({lng} {lat})"

        if role == "path":
            return (
                db.query(Ride)
                .filter(
                    Ride.route_geometry.isnot(None),
                    Ride.available_seats > 0,
                    Ride.status == RideStatus.ACTIVE,
                    Ride.departure_time > sa_func.now(),
                    sa_func.ST_DWithin(Ride.route_geometry, search_point, radius_m),
                )
                .all()
            )

        # Source / destination point-based fallback
        if role == "source":
            loc_col = Ride.source_location
        else:
            loc_col = Ride.destination_location

        return (
            db.query(Ride)
            .filter(
                loc_col.isnot(None),
                Ride.available_seats > 0,
                Ride.status == RideStatus.ACTIVE,
                Ride.departure_time > sa_func.now(),
                sa_func.ST_DWithin(loc_col, search_point, radius_m),
            )
            .all()
        )

    @staticmethod
    def _geocode(name: str) -> tuple[float, float] | None:
        """Simple mapping of common names to coordinates."""
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
            Ride.status == RideStatus.ACTIVE,
            Ride.departure_time > sa_func.now(),
        )

        s_coords = RideService._geocode(source)
        d_coords = RideService._geocode(destination)

        if s_coords and d_coords:
            # Smart Spatial Search: Both source and destination points must be near the route
            s_point = f"SRID=4326;POINT({s_coords[1]} {s_coords[0]})"
            d_point = f"SRID=4326;POINT({d_coords[1]} {d_coords[0]})"
            query = query.filter(
                Ride.route_geometry.isnot(None),
                sa_func.ST_DWithin(Ride.route_geometry, s_point, 5000), # 5km tolerance
                sa_func.ST_DWithin(Ride.route_geometry, d_point, 5000), # 5km tolerance
            )
        else:
            # Fallback to substring matching
            query = query.filter(
                Ride.source.ilike(f"%{source}%"),
                Ride.destination.ilike(f"%{destination}%"),
            )

        runs = query.all()
        
        # Convert geometry to WKT for all results
        from geoalchemy2 import functions as ga_func
        for r in runs:
            if r.route_geometry:
                r.route_geometry = db.query(ga_func.ST_AsText(Ride.route_geometry)).filter(Ride.id == r.id).scalar()
                
        result = [RideResponse.model_validate(r) for r in runs]
        redis_client.setex(cache_key, 60, json.dumps([r.model_dump(mode="json") for r in result]))
        return result
