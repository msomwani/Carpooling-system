-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT,                          -- nullable for Google OAuth users
    role VARCHAR(20) NOT NULL CHECK (role IN ('driver', 'passenger')),
    phone_number VARCHAR(20),
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    razorpay_account_id VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Ride status enum
CREATE TYPE ridestatus AS ENUM ('SCHEDULED', 'STARTED', 'COMPLETED', 'CANCELLED', 'MISSED_START');
CREATE TYPE ridecompletionsource AS ENUM ('DRIVER', 'SYSTEM');
CREATE TYPE bookingtripstatus AS ENUM ('BOOKED', 'READY_AT_PICKUP', 'BOARDED', 'DROPPED', 'NO_SHOW');

-- Rides table
CREATE TABLE rides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    source_lat DOUBLE PRECISION,
    source_lng DOUBLE PRECISION,
    destination VARCHAR(255) NOT NULL,
    destination_lat DOUBLE PRECISION,
    destination_lng DOUBLE PRECISION,
    source_location GEOGRAPHY(POINT, 4326),
    destination_location GEOGRAPHY(POINT, 4326),
    departure_time TIMESTAMP NOT NULL,
    total_seats INTEGER NOT NULL CHECK (total_seats > 0),
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0),
    status ridestatus NOT NULL DEFAULT 'SCHEDULED',
    actual_started_at TIMESTAMP,
    actual_completed_at TIMESTAMP,
    actual_start_lat DOUBLE PRECISION,
    actual_start_lng DOUBLE PRECISION,
    actual_complete_lat DOUBLE PRECISION,
    actual_complete_lng DOUBLE PRECISION,
    completed_by ridecompletionsource,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rides_source_lat_range CHECK (source_lat IS NULL OR (source_lat >= -90 AND source_lat <= 90)),
    CONSTRAINT chk_rides_source_lng_range CHECK (source_lng IS NULL OR (source_lng >= -180 AND source_lng <= 180)),
    CONSTRAINT chk_rides_destination_lat_range CHECK (destination_lat IS NULL OR (destination_lat >= -90 AND destination_lat <= 90)),
    CONSTRAINT chk_rides_destination_lng_range CHECK (destination_lng IS NULL OR (destination_lng >= -180 AND destination_lng <= 180)),
    CONSTRAINT chk_rides_source_coords_pair CHECK (
        (source_lat IS NULL AND source_lng IS NULL) OR
        (source_lat IS NOT NULL AND source_lng IS NOT NULL)
    ),
    CONSTRAINT chk_rides_destination_coords_pair CHECK (
        (destination_lat IS NULL AND destination_lng IS NULL) OR
        (destination_lat IS NOT NULL AND destination_lng IS NOT NULL)
    )
);



-- Bookings table
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_id UUID NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    passenger_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    seats_booked INTEGER NOT NULL CHECK (seats_booked > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING_PAYMENT', 'PAID_HELD', 'CONFIRMED', 'REFUNDED', 'CANCELLED')),
    trip_status bookingtripstatus NOT NULL DEFAULT 'BOOKED',
    boarded_seats INTEGER NOT NULL DEFAULT 0 CHECK (boarded_seats >= 0),
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    razorpay_transfer_id VARCHAR(100),
    passenger_ready_at TIMESTAMP,
    boarded_at TIMESTAMP,
    passenger_boarding_confirmed_at TIMESTAMP,
    settled_amount_paise INTEGER NOT NULL DEFAULT 0 CHECK (settled_amount_paise >= 0),
    refunded_amount_paise INTEGER NOT NULL DEFAULT 0 CHECK (refunded_amount_paise >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_rides_search ON rides(source, destination, departure_time);
CREATE INDEX idx_bookings_ride ON bookings(ride_id);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_bookings_status ON bookings(status);

CREATE INDEX idx_rides_source_coords ON rides(source_lat, source_lng);
CREATE INDEX idx_rides_destination_coords ON rides(destination_lat, destination_lng);
CREATE INDEX idx_rides_source_location ON rides USING GIST (source_location);
CREATE INDEX idx_rides_destination_location ON rides USING GIST (destination_location);

-- Partial unique index: only enforces uniqueness for CONFIRMED bookings
-- This allows multiple CANCELLED bookings but only one CONFIRMED booking per passenger per ride
CREATE UNIQUE INDEX unique_active_ride_passenger 
ON bookings (ride_id, passenger_id) 
WHERE status IN ('PENDING_PAYMENT', 'PAID_HELD', 'CONFIRMED');

-- Prevents duplicate booking requests
CREATE TABLE booking_idempotency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    booking_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Add to outbox event then to kafka
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Consumer idempotency tracking
CREATE TABLE processed_events (
    event_id UUID NOT NULL,
    consumer_name VARCHAR(100) NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, consumer_name)
);

-- Notification delivery audit
CREATE TABLE notification_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    channel VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    error TEXT,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notification_attempts_event_id ON notification_attempts(event_id);

-- Event-driven booking history projection
CREATE TABLE booking_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    ride_id UUID NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    correlation_id VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_booking_history_user_id ON booking_history(user_id);
CREATE INDEX idx_booking_history_occurred_at ON booking_history(occurred_at);
