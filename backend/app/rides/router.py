from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.common.db import SessionLocal
from app.rides.schemas import RideCreateRequest, RideResponse
from app.rides.service import RideService
from app.rides.models import Ride
from app.auth.dependencies import get_current_user_id


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
    

@router.get("/", response_model=List[RideResponse])
def search_rides(
    source: str,
    destination: str,
    db: Session = Depends(get_db),
):
    rides = db.query(Ride).filter(
        Ride.source == source,
        Ride.destination == destination,
        Ride.available_seats > 0
    ).all()

    return rides

