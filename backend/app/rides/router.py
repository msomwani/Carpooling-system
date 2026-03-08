from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.rides.schemas import RideCreateRequest, RideResponse
from app.rides.service import RideService
from app.rides.models import RideStatus
from app.auth.dependencies import get_current_user_id


router = APIRouter(prefix="/rides", tags=["Rides"])





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
    role: str = Query("source", pattern="^(source|destination)$"),
    db: Session = Depends(get_db),
):
    """Find ACTIVE rides within *radius_km* of (lat, lng)."""
    rides = RideService.search_nearby(db, lat=lat, lng=lng, radius_km=radius_km, role=role)
    return rides


@router.get("/", response_model=list[RideResponse])
def search_rides(
    source: str,
    destination: str,
    db: Session = Depends(get_db),
):
    return RideService.search_rides(db, source=source, destination=destination)
