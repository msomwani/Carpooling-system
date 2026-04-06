from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from app.common.db import get_db
from app.vehicles.schemas import VehicleCreateRequest, VehicleResponse
from app.vehicles.service import VehicleService
from app.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

# Import rate limiter for state‑changing endpoints
from app.auth.router import limiter


@router.post("", response_model=VehicleResponse)
@limiter.limit("10/minute")
def add_vehicle(
    payload: VehicleCreateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        vehicle = VehicleService.add_vehicle(
            db=db,
            owner_id=user_id,
            make=payload.make,
            model=payload.model,
            color=payload.color,
            license_plate=payload.license_plate,
            vehicle_type=payload.type,
        )
        return vehicle
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me", response_model=list[VehicleResponse])
def get_my_vehicles(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return VehicleService.get_my_vehicles(db, owner_id=user_id)


@router.delete("/{vehicle_id}")
@limiter.limit("10/minute")
def delete_vehicle(
    vehicle_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        VehicleService.delete_vehicle(db, vehicle_id=vehicle_id, owner_id=user_id)
        return Response(status_code=204)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
