-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
    otp_code VARCHAR(6),
    otp_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Ride status enum
CREATE TYPE ridestatus AS ENUM ('ACTIVE', 'COMPLETED', 'CANCELLED');

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
    departure_time TIMESTAMP NOT NULL,
    total_seats INTEGER NOT NULL CHECK (total_seats > 0),
    available_seats INTEGER NOT NULL CHECK (available_seats >= 0),
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
    status VARCHAR(20) NOT NULL CHECK (status IN ('CONFIRMED', 'CANCELLED')),
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

-- Partial unique index: only enforces uniqueness for CONFIRMED bookings
-- This allows multiple CANCELLED bookings but only one CONFIRMED booking per passenger per ride
CREATE UNIQUE INDEX unique_active_ride_passenger 
ON bookings (ride_id, passenger_id) 
WHERE status = 'CONFIRMED';

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
