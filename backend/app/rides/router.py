from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.rides.schemas import RideCreateRequest, RideResponse, RideDetailResponse
from app.rides.service import RideService
from app.rides.models import RideStatus
from app.auth.dependencies import get_current_user_id


router = APIRouter(prefix="/rides", tags=["Rides"])





@router.post("", response_model=RideResponse)
def create_ride(
    payload: RideCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        ride = RideService.create_ride(
            db=db,
            driver_id=user_id,
            departure_time=payload.departure_time,
            total_seats=payload.total_seats,
            price_per_seat=payload.price_per_seat,
            vehicle_id=payload.vehicle_id,
            source=payload.source,
            source_lat=payload.source_lat,
            source_lng=payload.source_lng,
            destination=payload.destination,
            destination_lat=payload.destination_lat,
            destination_lng=payload.destination_lng,
            route_geometry=payload.route_geometry
        )
        return ride
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))




@router.post("/{ride_id}/complete", response_model=RideResponse)
def complete_ride(
    ride_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Mark a ride as COMPLETED. Only the owning driver can call this."""
    try:
        ride = RideService.complete_ride(db, ride_id=ride_id, driver_id=user_id)
        return ride
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ride_id}/cancel", response_model=RideResponse)
def cancel_ride(
    ride_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Cancel a ride. Only the owning driver can call this."""
    correlation_id = request.state.correlation_id if hasattr(request.state, "correlation_id") else None
    
    try:
        ride = RideService.cancel_ride(
            db, 
            ride_id=ride_id, 
            driver_id=user_id,
            correlation_id=correlation_id
        )
        return ride
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/nearby", response_model=list[RideResponse])
def search_rides_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    role: str = Query("source", pattern="^(source|destination|path)$"),
    db: Session = Depends(get_db),
):
    """
    Find ACTIVE rides within *radius_km* of (lat, lng).

    - **role=source** (default): rides starting near the point.
    - **role=destination**: rides ending near the point.
    - **role=path**: rides whose full route passes near the point (uses `route_geometry` LineString).
    """
    rides = RideService.search_nearby(db, lat=lat, lng=lng, radius_km=radius_km, role=role)
    return rides


@router.get("", response_model=list[RideResponse])
def search_rides(
    source: str,
    destination: str,
    db: Session = Depends(get_db),
):
    return RideService.search_rides(db, source=source, destination=destination)

@router.get("/me", response_model=list[RideResponse])
def get_my_rides(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Fetch all rides created by the authenticated driver."""
    return [RideResponse.model_validate(r) for r in RideService.get_driver_rides(db, driver_id=user_id)]


@router.get("/{ride_id}", response_model=RideDetailResponse)
def get_ride(
    ride_id: str,
    db: Session = Depends(get_db),
):
    """Fetch details for a specific ride by ID."""
    ride_details = RideService.get_ride_by_id(db, ride_id=ride_id)
    if not ride_details:
        raise HTTPException(status_code=404, detail="Ride not found")
    return ride_details
