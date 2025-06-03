-- Migration: Initial Schema - Core Tables
-- Description: Creates the core tables for TripSage travel planning system
-- Created: 2025-05-08

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT,
    email TEXT,
    preferences_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT users_email_unique UNIQUE (email)
);

COMMENT ON TABLE users IS 'Users of the TripSage travel planning system';
COMMENT ON COLUMN users.id IS 'Unique identifier for the user';
COMMENT ON COLUMN users.name IS 'User''s display name';
COMMENT ON COLUMN users.email IS 'User''s email address for identification and notifications';
COMMENT ON COLUMN users.preferences_json IS 'User preferences stored as JSONB, including travel preferences, notification settings, etc.';
COMMENT ON COLUMN users.created_at IS 'Timestamp when the user record was created';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when the user record was last updated';

-- Create trips table
CREATE TABLE IF NOT EXISTS trips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT NOT NULL,
    budget NUMERIC NOT NULL,
    travelers INTEGER NOT NULL,
    status TEXT NOT NULL,
    trip_type TEXT NOT NULL,
    flexibility JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT trips_date_check CHECK (end_date >= start_date),
    CONSTRAINT trips_travelers_check CHECK (travelers > 0),
    CONSTRAINT trips_budget_check CHECK (budget > 0),
    CONSTRAINT trips_status_check CHECK (status IN ('planning', 'booked', 'completed', 'cancelled')),
    CONSTRAINT trips_type_check CHECK (trip_type IN ('leisure', 'business', 'family', 'solo', 'other'))
);

COMMENT ON TABLE trips IS 'Travel trips planned by users';
COMMENT ON COLUMN trips.id IS 'Unique identifier for the trip';
COMMENT ON COLUMN trips.name IS 'Name or title of the trip';
COMMENT ON COLUMN trips.start_date IS 'Trip start date';
COMMENT ON COLUMN trips.end_date IS 'Trip end date';
COMMENT ON COLUMN trips.destination IS 'Primary destination of the trip';
COMMENT ON COLUMN trips.budget IS 'Total budget allocated for the trip';
COMMENT ON COLUMN trips.travelers IS 'Number of travelers for the trip';
COMMENT ON COLUMN trips.status IS 'Current status of the trip (planning, booked, completed, cancelled)';
COMMENT ON COLUMN trips.trip_type IS 'Type of trip (leisure, business, family, solo, other)';
COMMENT ON COLUMN trips.flexibility IS 'JSON containing flexibility parameters for dates, budget, etc.';
COMMENT ON COLUMN trips.created_at IS 'Timestamp when the trip was created';
COMMENT ON COLUMN trips.updated_at IS 'Timestamp when the trip was last updated';

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for users table
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create trigger for trips table
CREATE TRIGGER update_trips_updated_at
BEFORE UPDATE ON trips
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();