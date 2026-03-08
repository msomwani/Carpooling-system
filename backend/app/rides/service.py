import json
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Float
from datetime import datetime, timezone
from app.rides.models import Ride, RideStatus
from app.users.models import User
from app.common.redis import redis_client
from app.rides.schemas import RideResponse

# Earth radius in kilometres (mean)
_EARTH_RADIUS_KM = 6371.0


class RideService:

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
    ) -> Ride:
        # Validate temporal constraints
        if departure_time:
            now = datetime.now(timezone.utc)
            if departure_time < now:
                raise ValueError("Cannot create a ride in the past")

        # Any authenticated user can create a ride — role is a preference, not a gate
        ride = Ride(
            driver_id=driver_id,
            source=source,
            source_lat=source_lat,
            source_lng=source_lng,
            destination=destination,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            departure_time=departure_time,
            total_seats=total_seats,
            available_seats=total_seats,
            status=RideStatus.ACTIVE,
        )

        db.add(ride)
        db.commit()
        db.refresh(ride)

        try:
            cache_pattern = "rides:*"
            for key in redis_client.scan_iter(match=cache_pattern):
                redis_client.delete(key)
        except Exception:
            pass

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
    def complete_ride(db: Session, *, ride_id: str, driver_id: str) -> Ride:
        """Mark a ride as COMPLETED. Only the owning driver can do this."""
        ride = RideService._get_ride_owned_by(db, ride_id, driver_id)
        
        if ride.departure_time:
            now = datetime.now(timezone.utc)
            if ride.departure_time > now:
                raise ValueError("Cannot complete a ride before its departure time")
                
        ride.status = RideStatus.COMPLETED
        db.commit()
        db.refresh(ride)

        try:
            cache_pattern = "rides:*"
            for key in redis_client.scan_iter(match=cache_pattern):
                redis_client.delete(key)
        except Exception:
            pass

        return ride

    @staticmethod
    def cancel_ride(db: Session, *, ride_id: str, driver_id: str) -> Ride:
        """Cancel a ride. Only the owning driver can do this."""
        ride = RideService._get_ride_owned_by(db, ride_id, driver_id)
        ride.status = RideStatus.CANCELLED
        db.commit()
        db.refresh(ride)

        try:
            cache_pattern = "rides:*"
            for key in redis_client.scan_iter(match=cache_pattern):
                redis_client.delete(key)
        except Exception:
            pass

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
        Find ACTIVE rides whose source or destination coordinates fall within
        *radius_km* of the given (lat, lng) using the Haversine formula.
        """
        if role == "source":
            lat_col = Ride.source_lat
            lng_col = Ride.source_lng
        else:
            lat_col = Ride.destination_lat
            lng_col = Ride.destination_lng

        # Haversine distance expression (returns km)
        lat_rad = sa_func.radians(cast(lat, Float))
        lng_rad = sa_func.radians(cast(lng, Float))

        dlat = sa_func.radians(lat_col) - lat_rad
        dlng = sa_func.radians(lng_col) - lng_rad

        a = (
            sa_func.power(sa_func.sin(dlat / 2), 2)
            + sa_func.cos(lat_rad)
            * sa_func.cos(sa_func.radians(lat_col))
            * sa_func.power(sa_func.sin(dlng / 2), 2)
        )
        distance = _EARTH_RADIUS_KM * 2 * sa_func.atan2(sa_func.sqrt(a), sa_func.sqrt(1 - a))

        return (
            db.query(Ride)
            .filter(
                lat_col.isnot(None),
                lng_col.isnot(None),
                Ride.available_seats > 0,
                Ride.status == RideStatus.ACTIVE,   # ← only ACTIVE rides
                distance <= radius_km,
            )
            .all()
        )

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

        rides = db.query(Ride).filter(
            Ride.source == source,
            Ride.destination == destination,
            Ride.available_seats > 0,
            Ride.status == RideStatus.ACTIVE,
        ).all()

        result = [RideResponse.model_validate(r) for r in rides]
        redis_client.setex(cache_key, 60, json.dumps([r.model_dump(mode="json") for r in result]))
        return result
