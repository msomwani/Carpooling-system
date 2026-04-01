"""
Unit tests for Advanced Route Matching (LineString-based search).

Tests the `search_nearby(role="path")` method in RideService, which uses
PostGIS ST_DWithin on the `route_geometry` LineString to find rides that
pass near a passenger's location — not just at the start/end points.

Real PostGIS queries are used here (via the test DB), so these tests require
the test database to have PostGIS installed.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.rides.service import RideService
from app.rides.models import Ride, RideStatus
from app.vehicles.models import Vehicle, VehicleType


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_driver(db):
    from app.users.models import User
    driver = User(
        id=uuid4(),
        name="Route Driver",
        email=f"route_driver_{uuid4()}@test.com",
        password_hash="hashed",
        role="driver",
        is_email_verified=True,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@pytest.fixture
def sample_vehicle(db, sample_driver):
    vehicle = Vehicle(
        id=uuid4(),
        owner_id=sample_driver.id,
        make="Toyota",
        model="Innova",
        color="White",
        license_plate=f"GJ-{uuid4().hex[:4].upper()}",
        type=VehicleType.CAR,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def _make_ride(db, driver_id, route_wkt=None, status=RideStatus.SCHEDULED, seats=4):
    """Helper: insert a Ride directly with a raw WKT route_geometry."""
    ride = Ride(
        id=uuid4(),
        driver_id=driver_id,
        source="Vadodara",
        source_lat=22.3072,
        source_lng=73.1812,
        source_location="SRID=4326;POINT(73.1812 22.3072)",
        destination="Ahmedabad",
        destination_lat=23.0225,
        destination_lng=72.5714,
        destination_location="SRID=4326;POINT(72.5714 23.0225)",
        departure_time=datetime.now(timezone.utc) + timedelta(hours=3),
        total_seats=seats,
        available_seats=seats,
        price_per_seat=100,
        status=status,
        route_geometry=f"SRID=4326;{route_wkt}" if route_wkt else None,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride


# ──────────────────────────────────────────────────────────
# The actual LineString used in tests:
# Represents a rough Vadodara → Anand → Ahmedabad driving path.
# WGS-84 coordinates in (lng lat) order as required by PostGIS.
# ──────────────────────────────────────────────────────────
VADODARA_TO_AHMEDABAD_LINESTRING = (
    "LINESTRING("
    "73.1812 22.3072,"   # Vadodara (source)
    "73.0000 22.5500,"   # Near Anand (midpoint — passenger location used in tests)
    "72.5714 23.0225"    # Ahmedabad (destination)
    ")"
)

# A midpoint on the route — passenger stands here
MIDPOINT_LAT, MIDPOINT_LNG = 22.5500, 73.0000

# A point far from the route (~60 km east)
FAR_LAT, FAR_LNG = 22.5500, 73.7000


# ──────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────

class TestAdvancedRouteMatching:

    def test_path_mode_finds_ride_along_midpoint(self, db, sample_driver):
        """
        A ride whose route_geometry passes through ~Anand (midpoint) should be
        returned when we search near that midpoint using role='path'.
        """
        _make_ride(db, sample_driver.id, route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING)

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=MIDPOINT_LAT,
                lng=MIDPOINT_LNG,
                radius_km=5.0,
                role="path",
            )

        assert len(results) == 1, "Should find the ride passing through the midpoint"

    def test_path_mode_excludes_ride_far_from_route(self, db, sample_driver):
        """
        A point ~60 km east of the route should return no results in path mode.
        """
        _make_ride(db, sample_driver.id, route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING)

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=FAR_LAT,
                lng=FAR_LNG,
                radius_km=5.0,
                role="path",
            )

        assert len(results) == 0, "Should not find the ride when the point is far away"

    def test_path_mode_excludes_rides_without_route_geometry(self, db, sample_driver):
        """
        Rides that have NO route_geometry stored should be invisible in path mode,
        even if the search point happens to be near the start/end.
        """
        _make_ride(db, sample_driver.id, route_wkt=None)  # no geometry

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=22.3072,    # exactly at Vadodara source
                lng=73.1812,
                radius_km=1.0,
                role="path",
            )

        assert len(results) == 0, "Rides without route_geometry should never be returned in path mode"

    def test_path_mode_excludes_cancelled_rides(self, db, sample_driver):
        """
        CANCELLED rides should be excluded even if the route passes the search point.
        """
        _make_ride(
            db,
            sample_driver.id,
            route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING,
            status=RideStatus.CANCELLED,
        )

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=MIDPOINT_LAT,
                lng=MIDPOINT_LNG,
                radius_km=5.0,
                role="path",
            )

        assert len(results) == 0, "Cancelled rides should not be returned"

    def test_path_mode_excludes_full_rides(self, db, sample_driver):
        """
        Rides with 0 available seats should not appear in path search results.
        """
        _make_ride(
            db,
            sample_driver.id,
            route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING,
            seats=0,
        )

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=MIDPOINT_LAT,
                lng=MIDPOINT_LNG,
                radius_km=5.0,
                role="path",
            )

        assert len(results) == 0, "Full rides (0 seats) should not be returned"

    def test_source_mode_still_works_correctly(self, db, sample_driver):
        """
        Regression test: role='source' must still work after the path-mode addition.
        """
        _make_ride(
            db,
            sample_driver.id,
            route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING,
        )

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=22.3072,    # Vadodara source
                lng=73.1812,
                radius_km=2.0,
                role="source",
            )

        assert len(results) == 1, "role='source' should still find rides near the source point"

    def test_multiple_rides_only_matching_route_returned(self, db, sample_driver):
        """
        Two rides exist — only the one with a route passing through the midpoint
        should be returned in path mode.
        """
        # Ride 1: passes through the midpoint
        _make_ride(db, sample_driver.id, route_wkt=VADODARA_TO_AHMEDABAD_LINESTRING)

        # Ride 2: a short route in a completely different area (Surat → Mumbai)
        surat_mumbai = (
            "LINESTRING("
            "72.8311 21.1702,"   # Surat
            "72.8777 19.0760"    # Mumbai
            ")"
        )
        _make_ride(db, sample_driver.id, route_wkt=surat_mumbai)

        with patch("app.common.redis.redis_client"):
            results = RideService.search_nearby(
                db,
                lat=MIDPOINT_LAT,
                lng=MIDPOINT_LNG,
                radius_km=5.0,
                role="path",
            )

        assert len(results) == 1, "Only the ride passing through the midpoint should be returned"
