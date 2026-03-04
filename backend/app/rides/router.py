from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import json

from app.common.db import SessionLocal
from app.rides.schemas import RideCreateRequest, RideResponse
from app.rides.service import RideService
from app.rides.models import Ride
from app.auth.dependencies import get_current_user_id
from app.common.redis import redis_client


router = APIRouter(prefix="/rides", tags=["Rides"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=RideResponse)
def create_ride(
    payload: RideCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        ride = RideService.create_ride(
            db=db,
            driver_id=user_id,
            **payload.model_dump()
        )
        return ride
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/nearby", response_model=list[RideResponse])
def search_rides_nearby(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10.0, gt=0, le=500, description="Search radius in km"),
    role: str = Query("source", pattern="^(source|destination)$", description="Match source or destination"),
    db: Session = Depends(get_db),
):
    """Find rides whose source or destination is within *radius_km* of (lat, lng)."""
    rides = RideService.search_nearby(
        db, lat=lat, lng=lng, radius_km=radius_km, role=role
    )
    return [
        RideResponse(
            id=r.id,
            source=r.source,
            source_lat=r.source_lat,
            source_lng=r.source_lng,
            destination=r.destination,
            destination_lat=r.destination_lat,
            destination_lng=r.destination_lng,
            departure_time=r.departure_time,
            available_seats=r.available_seats,
        )
        for r in rides
    ]


@router.get("/", response_model=list[RideResponse])
def search_rides(
    source: str,
    destination: str,
    db: Session = Depends(get_db),
):
    cache_key = f"rides:{source}:{destination}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    rides = db.query(Ride).filter(
        Ride.source == source,
        Ride.destination == destination,
        Ride.available_seats > 0
    ).all()

    result = [
        RideResponse(
            id=r.id,
            source=r.source,
            source_lat=r.source_lat,
            source_lng=r.source_lng,
            destination=r.destination,
            destination_lat=r.destination_lat,
            destination_lng=r.destination_lng,
            departure_time=r.departure_time,
            available_seats=r.available_seats,
        )
        for r in rides
    ]

    redis_client.setex(cache_key, 60, json.dumps([r.model_dump(mode="json") for r in result]))
    return result
