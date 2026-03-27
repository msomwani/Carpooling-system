import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app
from app.vehicles.models import Vehicle, VehicleType
from app.auth.dependencies import get_current_user_id

def test_delete_vehicle_unauthorized(client, db, sample_driver, sample_passenger):
    """Issue 6: Verify that deleting another user's vehicle returns 403."""
    # 1. Create a vehicle for the driver
    vehicle = Vehicle(
        id=uuid4(),
        owner_id=sample_driver.id,
        make="Toyota",
        model="Camry",
        color="Silver",
        license_plate="OWNER-123",
        type=VehicleType.CAR
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    # 2. Mock authentication as the passenger
    app.dependency_overrides[get_current_user_id] = lambda: str(sample_passenger.id)
    
    # 3. Act: Attempt to delete driver's vehicle as passenger
    response = client.delete(f"/vehicles/{vehicle.id}")
    
    # 4. Assert: Should return 403
    assert response.status_code == 403
    assert "You do not own this vehicle" in response.json()["detail"]
    
    app.dependency_overrides.clear()

def test_add_vehicle_invalid_type(client, sample_driver):
    """Issue 6: Verify that invalid vehicle type returns 400."""
    app.dependency_overrides[get_current_user_id] = lambda: str(sample_driver.id)
    
    payload = {
        "make": "Tesla",
        "model": "Model 3",
        "color": "Red",
        "license_plate": "INVALID-TYPE",
        "type": "UNKNOWN_TYPE"
    }
    
    response = client.post("/vehicles", json=payload)
    
    # Enum validation usually returns 422 in FastAPI, but if it hits our service and fails, it should be 400
    # Let's check what actually happens.
    assert response.status_code in [400, 422]
    
    app.dependency_overrides.clear()
