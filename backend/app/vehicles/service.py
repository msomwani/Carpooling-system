from sqlalchemy.orm import Session
from app.vehicles.models import Vehicle, VehicleType
from uuid import UUID

class VehicleService:

    @staticmethod
    def add_vehicle(db: Session, *, owner_id: str, make: str, model: str, color: str, license_plate: str, vehicle_type: str) -> Vehicle:
        import re
        normalized_plate = re.sub(r'[^A-Z0-9]', '', license_plate.upper())
        vehicle = Vehicle(
            owner_id=owner_id,
            make=make,
            model=model,
            color=color,
            license_plate=normalized_plate,
            type=VehicleType(vehicle_type)
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    @staticmethod
    def get_my_vehicles(db: Session, *, owner_id: str) -> list[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.owner_id == owner_id).all()

    @staticmethod
    def delete_vehicle(db: Session, *, vehicle_id: str, owner_id: str):
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError("Vehicle not found")
        if str(vehicle.owner_id) != str(owner_id):
            raise PermissionError("You do not own this vehicle")
        
        db.delete(vehicle)
        db.commit()
