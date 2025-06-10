-- Migration: Dependent Tables
-- Description: Creates tables that depend on core tables for TripSage travel planning system
-- Created: 2025-05-08

-- Create flights table
CREATE TABLE IF NOT EXISTS flights (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    airline TEXT,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    booking_link TEXT,
    segment_number INTEGER,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    booking_status TEXT DEFAULT 'viewed',
    data_source TEXT,
    CONSTRAINT flights_price_check CHECK (price >= 0),
    CONSTRAINT flights_time_check CHECK (arrival_time > departure_time),
    CONSTRAINT flights_booking_status_check CHECK (booking_status IN ('viewed', 'saved', 'booked', 'cancelled'))
);

COMMENT ON TABLE flights IS 'Flight options for trips';
COMMENT ON COLUMN flights.id IS 'Unique identifier for the flight';
COMMENT ON COLUMN flights.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN flights.origin IS 'Origin airport or city';
COMMENT ON COLUMN flights.destination IS 'Destination airport or city';
COMMENT ON COLUMN flights.airline IS 'Name of the airline';
COMMENT ON COLUMN flights.departure_time IS 'Scheduled departure time with timezone';
COMMENT ON COLUMN flights.arrival_time IS 'Scheduled arrival time with timezone';
COMMENT ON COLUMN flights.price IS 'Price of the flight in default currency';
COMMENT ON COLUMN flights.booking_link IS 'URL for booking the flight';
COMMENT ON COLUMN flights.segment_number IS 'Segment number for multi-leg flights';
COMMENT ON COLUMN flights.search_timestamp IS 'When this flight option was found';
COMMENT ON COLUMN flights.booking_status IS 'Status of the flight booking (viewed, saved, booked, cancelled)';
COMMENT ON COLUMN flights.data_source IS 'Source of the flight data (API provider)';

-- Create accommodations table
CREATE TABLE IF NOT EXISTS accommodations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    price_per_night NUMERIC NOT NULL,
    total_price NUMERIC NOT NULL,
    location TEXT NOT NULL,
    rating NUMERIC,
    amenities JSONB,
    booking_link TEXT,
    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    booking_status TEXT DEFAULT 'viewed',
    cancellation_policy TEXT,
    distance_to_center NUMERIC,
    neighborhood TEXT,
    CONSTRAINT accommodations_price_check CHECK (price_per_night >= 0),
    CONSTRAINT accommodations_total_price_check CHECK (total_price >= 0),
    CONSTRAINT accommodations_dates_check CHECK (check_out > check_in),
    CONSTRAINT accommodations_rating_check CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    CONSTRAINT accommodations_booking_status_check CHECK (booking_status IN ('viewed', 'saved', 'booked', 'cancelled')),
    CONSTRAINT accommodations_type_check CHECK (type IN ('hotel', 'apartment', 'hostel', 'resort', 'villa', 'house', 'other'))
);

COMMENT ON TABLE accommodations IS 'Accommodation options for trips';
COMMENT ON COLUMN accommodations.id IS 'Unique identifier for the accommodation';
COMMENT ON COLUMN accommodations.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN accommodations.name IS 'Name of the accommodation';
COMMENT ON COLUMN accommodations.type IS 'Type of accommodation (hotel, apartment, hostel, etc.)';
COMMENT ON COLUMN accommodations.check_in IS 'Check-in date';
COMMENT ON COLUMN accommodations.check_out IS 'Check-out date';
COMMENT ON COLUMN accommodations.price_per_night IS 'Price per night in default currency';
COMMENT ON COLUMN accommodations.total_price IS 'Total price for the entire stay';
COMMENT ON COLUMN accommodations.location IS 'Location of the accommodation';
COMMENT ON COLUMN accommodations.rating IS 'Rating of the accommodation (0-5 scale)';
COMMENT ON COLUMN accommodations.amenities IS 'List of amenities as JSON';
COMMENT ON COLUMN accommodations.booking_link IS 'URL for booking the accommodation';
COMMENT ON COLUMN accommodations.search_timestamp IS 'When this accommodation option was found';
COMMENT ON COLUMN accommodations.booking_status IS 'Status of the accommodation booking (viewed, saved, booked, cancelled)';
COMMENT ON COLUMN accommodations.cancellation_policy IS 'Description of the cancellation policy';
COMMENT ON COLUMN accommodations.distance_to_center IS 'Distance to city center or point of interest';
COMMENT ON COLUMN accommodations.neighborhood IS 'Name of the neighborhood or area';

-- Create transportation table
CREATE TABLE IF NOT EXISTS transportation (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    provider TEXT,
    pickup_date TIMESTAMP WITH TIME ZONE NOT NULL,
    dropoff_date TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    notes TEXT,
    booking_status TEXT DEFAULT 'viewed',
    CONSTRAINT transportation_price_check CHECK (price >= 0),
    CONSTRAINT transportation_dates_check CHECK (dropoff_date >= pickup_date),
    CONSTRAINT transportation_booking_status_check CHECK (booking_status IN ('viewed', 'saved', 'booked', 'cancelled')),
    CONSTRAINT transportation_type_check CHECK (type IN ('car_rental', 'public_transit', 'taxi', 'shuttle', 'ferry', 'train', 'bus', 'other'))
);

COMMENT ON TABLE transportation IS 'Transportation options for trips';
COMMENT ON COLUMN transportation.id IS 'Unique identifier for the transportation';
COMMENT ON COLUMN transportation.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN transportation.type IS 'Type of transportation (car_rental, public_transit, taxi, etc.)';
COMMENT ON COLUMN transportation.provider IS 'Name of the transportation provider';
COMMENT ON COLUMN transportation.pickup_date IS 'Pickup date and time';
COMMENT ON COLUMN transportation.dropoff_date IS 'Dropoff date and time';
COMMENT ON COLUMN transportation.price IS 'Price in default currency';
COMMENT ON COLUMN transportation.notes IS 'Additional notes or information';
COMMENT ON COLUMN transportation.booking_status IS 'Status of the transportation booking (viewed, saved, booked, cancelled)';

-- Create itinerary_items table
CREATE TABLE IF NOT EXISTS itinerary_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    date DATE NOT NULL,
    time TIME,
    description TEXT NOT NULL,
    cost NUMERIC,
    notes TEXT,
    CONSTRAINT itinerary_items_cost_check CHECK (cost IS NULL OR cost >= 0),
    CONSTRAINT itinerary_items_type_check CHECK (type IN ('activity', 'meal', 'transport', 'accommodation', 'other'))
);

COMMENT ON TABLE itinerary_items IS 'Items in a trip itinerary';
COMMENT ON COLUMN itinerary_items.id IS 'Unique identifier for the itinerary item';
COMMENT ON COLUMN itinerary_items.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN itinerary_items.type IS 'Type of itinerary item (activity, meal, transport, etc.)';
COMMENT ON COLUMN itinerary_items.date IS 'Date of the itinerary item';
COMMENT ON COLUMN itinerary_items.time IS 'Time of the itinerary item';
COMMENT ON COLUMN itinerary_items.description IS 'Description of the itinerary item';
COMMENT ON COLUMN itinerary_items.cost IS 'Cost of the itinerary item in default currency';
COMMENT ON COLUMN itinerary_items.notes IS 'Additional notes or information';

-- Create search_parameters table
CREATE TABLE IF NOT EXISTS search_parameters (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    parameter_json JSONB NOT NULL
);

COMMENT ON TABLE search_parameters IS 'Search parameters used for finding travel options';
COMMENT ON COLUMN search_parameters.id IS 'Unique identifier for the search parameters';
COMMENT ON COLUMN search_parameters.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN search_parameters.timestamp IS 'When the search was performed';
COMMENT ON COLUMN search_parameters.parameter_json IS 'Search parameters as JSON';

-- Create trip_notes table
CREATE TABLE IF NOT EXISTS trip_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    content TEXT NOT NULL
);

COMMENT ON TABLE trip_notes IS 'Notes attached to trips';
COMMENT ON COLUMN trip_notes.id IS 'Unique identifier for the trip note';
COMMENT ON COLUMN trip_notes.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN trip_notes.timestamp IS 'When the note was created';
COMMENT ON COLUMN trip_notes.content IS 'Content of the note';

-- Create trip_comparison table
CREATE TABLE IF NOT EXISTS trip_comparison (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    comparison_json JSONB NOT NULL
);

COMMENT ON TABLE trip_comparison IS 'Comparison data between different trip options';
COMMENT ON COLUMN trip_comparison.id IS 'Unique identifier for the trip comparison';
COMMENT ON COLUMN trip_comparison.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN trip_comparison.comparison_json IS 'Comparison data as JSON';