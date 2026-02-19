import pytest
import threading
from uuid import uuid4
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.bookings.service import BookingService
from app.rides.models import Ride
from app.users.models import User
from app.common.db import SessionLocal


class TestConcurrency:
    """
    Critical tests to prove the system handles concurrent bookings correctly.
    These tests simulate real-world race conditions.
    """
    
    def test_concurrent_bookings_no_overbooking(self, db, sample_driver):
        """
        CRITICAL TEST: Simulate 10 passengers trying to book the last 4 seats simultaneously.
        Expected: Exactly 4 bookings succeed, 6 fail. No overbooking.
        """
        # Create a ride with only 4 seats
        ride = Ride(
            id=uuid4(),
            driver_id=sample_driver.id,
            source="Test Source",
            destination="Test Destination",
            departure_time=datetime.now() + timedelta(hours=2),
            total_seats=4,
            available_seats=4
        )
        db.add(ride)
        
        # Create 10 passengers
        passengers = []
        for i in range(10):
            passenger = User(
                id=uuid4(),
                name=f"Concurrent Passenger {i}",
                email=f"concurrent_{i}_{uuid4()}@test.com",
                password_hash="hash",
                role="passenger"
            )
            db.add(passenger)
            passengers.append(passenger)
        
        db.commit()
        
        # Track results
        successful_bookings = []
        failed_bookings = []
        lock = threading.Lock()
        
        def try_booking(passenger_index):
            """Each thread tries to book 1 seat."""
            # Each thread needs its own database session
            thread_db = SessionLocal()
            
            try:
                passenger = passengers[passenger_index]
                booking = BookingService.create_booking(
                    db=thread_db,
                    ride_id=ride.id,
                    passenger_id=passenger.id,
                    seats_requested=1,
                    idempotency_key=f"concurrent-test-{passenger_index}",
                    correlation_id=f"concurrent-corr-{passenger_index}"
                )
                
                with lock:
                    successful_bookings.append(booking.id)
                
                return True
            
            except ValueError as e:
                with lock:
                    failed_bookings.append(str(e))
                return False
            
            finally:
                thread_db.close()
        
        # Execute concurrent bookings using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(try_booking, i) for i in range(10)]
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        # Critical assertions
        assert len(successful_bookings) == 4, f"Expected exactly 4 successful bookings, got {len(successful_bookings)}"
        assert len(failed_bookings) == 6, f"Expected exactly 6 failed bookings, got {len(failed_bookings)}"
        
        # Verify final seat count
        db.refresh(ride)
        assert ride.available_seats == 0, f"Expected 0 available seats, got {ride.available_seats}"
        
        # Verify no duplicate bookings
        assert len(set(successful_bookings)) == len(successful_bookings), "Found duplicate booking IDs"
    
    def test_concurrent_bookings_multiple_seats(self, db, sample_driver):
        """
        Test concurrent bookings where each passenger requests multiple seats.
        10 passengers each try to book 2 seats, but only 6 seats available.
        Expected: 3 succeed (3 * 2 = 6), 7 fail.
        """
        # Create ride with 6 seats
        ride = Ride(
            id=uuid4(),
            driver_id=sample_driver.id,
            source="Multi-seat Source",
            destination="Multi-seat Destination",
            departure_time=datetime.now() + timedelta(hours=3),
            total_seats=6,
            available_seats=6
        )
        db.add(ride)
        
        # Create 10 passengers
        passengers = []
        for i in range(10):
            passenger = User(
                id=uuid4(),
                name=f"Multi-seat Passenger {i}",
                email=f"multiseat_{i}_{uuid4()}@test.com",
                password_hash="hash",
                role="passenger"
            )
            db.add(passenger)
            passengers.append(passenger)
        
        db.commit()
        
        successful_count = [0]
        failed_count = [0]
        lock = threading.Lock()
        
        def try_booking_2_seats(passenger_index):
            thread_db = SessionLocal()
            
            try:
                passenger = passengers[passenger_index]
                BookingService.create_booking(
                    db=thread_db,
                    ride_id=ride.id,
                    passenger_id=passenger.id,
                    seats_requested=2,
                    idempotency_key=f"multi-seat-{passenger_index}",
                    correlation_id=f"multi-seat-corr-{passenger_index}"
                )
                
                with lock:
                    successful_count[0] += 1
                
            except ValueError:
                with lock:
                    failed_count[0] += 1
            
            finally:
                thread_db.close()
        
        # Execute concurrent bookings
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(try_booking_2_seats, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()
        
        # Assertions
        assert successful_count[0] == 3, f"Expected 3 successful bookings, got {successful_count[0]}"
        assert failed_count[0] == 7, f"Expected 7 failed bookings, got {failed_count[0]}"
        
        db.refresh(ride)
        assert ride.available_seats == 0
    
    def test_concurrent_idempotency(self, db, sample_ride, sample_passenger):
        """
        Test that concurrent requests with same idempotency key only create one booking.
        Simulate network retry scenario where same request is sent 5 times simultaneously.
        """
        idempotency_key = "concurrent-idempotency-test"
        booking_ids = []
        lock = threading.Lock()
        
        def try_booking_with_same_key():
            thread_db = SessionLocal()
            
            try:
                booking = BookingService.create_booking(
                    db=thread_db,
                    ride_id=sample_ride.id,
                    passenger_id=sample_passenger.id,
                    seats_requested=1,
                    idempotency_key=idempotency_key,  # Same key for all
                    correlation_id=f"idempotency-corr-{threading.current_thread().name}"
                )
                
                with lock:
                    booking_ids.append(booking.id)
            
            finally:
                thread_db.close()
        
        # Execute 5 concurrent requests with same idempotency key
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_booking_with_same_key) for _ in range(5)]
            for future in as_completed(futures):
                future.result()
        
        # All should return the same booking ID
        assert len(booking_ids) == 5
        assert len(set(booking_ids)) == 1, "Idempotency failed: created multiple bookings"
        
        # Verify only 1 seat was deducted
        db.refresh(sample_ride)
        assert sample_ride.available_seats == 3  # Started with 4
    
    def test_concurrent_cancel_and_rebook(self, db, sample_ride, sample_passenger):
        """
        Test race condition: one thread cancels while another tries to rebook.
        This tests the robustness of status checks and locking.
        """
        # Create initial booking
        booking = BookingService.create_booking(
            db=db,
            ride_id=sample_ride.id,
            passenger_id=sample_passenger.id,
            seats_requested=1,
            idempotency_key="race-test-1",
            correlation_id="race-corr-1"
        )
        
        from app.bookings.cancel_service import CancellationService
        
        results = []
        lock = threading.Lock()
        
        def cancel_booking():
            thread_db = SessionLocal()
            try:
                CancellationService.cancel_booking(
                    db=thread_db,
                    booking_id=str(booking.id),
                    user_id=str(sample_passenger.id),
                    correlation_id="race-cancel"
                )
                with lock:
                    results.append("cancelled")
            except Exception as e:
                with lock:
                    results.append(f"cancel_error: {e}")
            finally:
                thread_db.close()
        
        def rebook_ride():
            thread_db = SessionLocal()
            try:
                # Small delay to let cancel happen first
                import time
                time.sleep(0.01)
                
                BookingService.create_booking(
                    db=thread_db,
                    ride_id=sample_ride.id,
                    passenger_id=sample_passenger.id,
                    seats_requested=1,
                    idempotency_key="race-test-2",
                    correlation_id="race-rebook"
                )
                with lock:
                    results.append("rebooked")
            except Exception as e:
                with lock:
                    results.append(f"rebook_error: {e}")
            finally:
                thread_db.close()
        
        # Execute concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(cancel_booking),
                executor.submit(rebook_ride)
            ]
            for future in as_completed(futures):
                future.result()
        
        # Should complete without errors
        assert len(results) == 2
        assert "cancelled" in results
        assert "rebooked" in results or any("rebook_error" in r for r in results)
    
    def test_stress_test_100_concurrent_requests(self, db, sample_driver):
        """
        Stress test: 100 passengers trying to book a ride with 10 seats.
        This is a real-world scenario for popular rides.
        """
        # Create ride with 10 seats
        ride = Ride(
            id=uuid4(),
            driver_id=sample_driver.id,
            source="Popular Route",
            destination="Popular Destination",
            departure_time=datetime.now() + timedelta(hours=5),
            total_seats=10,
            available_seats=10
        )
        db.add(ride)
        
        # Create 100 passengers
        passengers = []
        for i in range(100):
            passenger = User(
                id=uuid4(),
                name=f"Stress Passenger {i}",
                email=f"stress_{i}_{uuid4()}@test.com",
                password_hash="hash",
                role="passenger"
            )
            db.add(passenger)
            passengers.append(passenger)
        
        db.commit()
        
        successful = [0]
        failed = [0]
        lock = threading.Lock()
        
        def try_booking(idx):
            thread_db = SessionLocal()
            try:
                BookingService.create_booking(
                    db=thread_db,
                    ride_id=ride.id,
                    passenger_id=passengers[idx].id,
                    seats_requested=1,
                    idempotency_key=f"stress-{idx}",
                    correlation_id=f"stress-corr-{idx}"
                )
                with lock:
                    successful[0] += 1
            except ValueError:
                with lock:
                    failed[0] += 1
            finally:
                thread_db.close()
        
        # Execute with 20 concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(try_booking, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()
        
        # Critical assertions
        assert successful[0] == 10, f"Expected 10 successful, got {successful[0]}"
        assert failed[0] == 90, f"Expected 90 failed, got {failed[0]}"
        
        db.refresh(ride)
        assert ride.available_seats == 0
        
        print(f"\n✅ Stress Test Passed: {successful[0]} bookings succeeded, {failed[0]} rejected")