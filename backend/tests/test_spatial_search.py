import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.rides.service import RideService
from app.rides.models import Ride, RideStatus

def test_spatial_search_nearby(db: Session, test_user, test_vehicle):
    # 1. Create a ride in Vadodara (Source: Alkapuri, Dest: Makarpura)
    # Alkapuri: 22.3129, 73.1642
    # Makarpura: 22.2575, 73.1947
    
    departure = datetime.now(timezone.utc) + timedelta(days=1)
    
    ride = RideService.create_ride(
        db,
        driver_id=test_user.id,
        source="Alkapuri",
        source_lat=22.3129,
        source_lng=73.1642,
        destination="Makarpura",
        destination_lat=22.2575,
        destination_lng=73.1947,
        departure_time=departure,
        total_seats=4,
        vehicle_id=test_vehicle.id
    )
    
    # 2. Search from a point NEAR Alkapuri (e.g., 1km away)
    # Railway Station is ~2km from Alkapuri
    results = RideService.search_nearby(
        db,
        lat=22.3106, # Near Alkapuri
        lng=73.1812,
        radius_km=5.0,
        role="source"
    )
    
    assert len(results) > 0
    assert results[0].id == ride.id
    
    # 3. Search from a point FAR away (e.g., Ahmedabad ~100km away)
    far_results = RideService.search_nearby(
        db,
        lat=23.0225,
        lng=72.5714,
        radius_km=5.0,
        role="source"
    )
    
    assert len(far_results) == 0

def test_spatial_backfill_logic(db: Session, test_user, test_vehicle):
    # This tests the logic that would be used in the migration
    # Insert a ride using raw SQL to bypass the service layer's new logic
    ride_id = "550e8400-e29b-41d4-a716-446655440000"
    departure = datetime.now(timezone.utc) + timedelta(days=2)
    
    db.execute(sa_text(f"""
        INSERT INTO rides (id, driver_id, source, source_lat, source_lng, destination, destination_lat, destination_lng, departure_time, total_seats, available_seats, status)
        VALUES ('{ride_id}', '{test_user.id}', 'Source', 22.3, 73.1, 'Dest', 22.4, 73.2, '{departure.isoformat()}', 4, 4, 'ACTIVE')
    """))
    db.commit()
    
    # Run the backfill SQL
    db.execute("""
        UPDATE rides 
        SET source_location = ST_SetSRID(ST_MakePoint(source_lng, source_lat), 4326)::geography,
            destination_location = ST_SetSRID(ST_MakePoint(destination_lng, destination_lat), 4326)::geography
        WHERE id = :ride_id
    """, {"ride_id": ride_id})
    db.commit()
    
    # Verify the backfill
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    assert ride.source_location is not None
    
    # Test search on backfilled data
    results = RideService.search_nearby(db, lat=22.3, lng=73.1, radius_km=1.0)
    assert len(results) == 1
    assert str(results[0].id) == ride_id

from sqlalchemy import text as sa_text
