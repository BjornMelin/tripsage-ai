-- Migration: Rollback
-- Description: Rollback script to undo all schema changes for the TripSage travel planning system
-- Created: 2025-05-08

-- Drop indexes
DROP INDEX IF EXISTS idx_trips_start_date;
DROP INDEX IF EXISTS idx_trips_end_date;
DROP INDEX IF EXISTS idx_trips_destination;
DROP INDEX IF EXISTS idx_trips_status;
DROP INDEX IF EXISTS idx_trips_trip_type;

DROP INDEX IF EXISTS idx_flights_trip_id;
DROP INDEX IF EXISTS idx_flights_origin;
DROP INDEX IF EXISTS idx_flights_destination;
DROP INDEX IF EXISTS idx_flights_departure_time;
DROP INDEX IF EXISTS idx_flights_price;
DROP INDEX IF EXISTS idx_flights_booking_status;
DROP INDEX IF EXISTS idx_flights_search_timestamp;

DROP INDEX IF EXISTS idx_accommodations_trip_id;
DROP INDEX IF EXISTS idx_accommodations_location;
DROP INDEX IF EXISTS idx_accommodations_check_in;
DROP INDEX IF EXISTS idx_accommodations_check_out;
DROP INDEX IF EXISTS idx_accommodations_price_per_night;
DROP INDEX IF EXISTS idx_accommodations_total_price;
DROP INDEX IF EXISTS idx_accommodations_rating;
DROP INDEX IF EXISTS idx_accommodations_booking_status;
DROP INDEX IF EXISTS idx_accommodations_search_timestamp;
DROP INDEX IF EXISTS idx_accommodations_type;

DROP INDEX IF EXISTS idx_transportation_trip_id;
DROP INDEX IF EXISTS idx_transportation_type;
DROP INDEX IF EXISTS idx_transportation_pickup_date;
DROP INDEX IF EXISTS idx_transportation_price;
DROP INDEX IF EXISTS idx_transportation_booking_status;

DROP INDEX IF EXISTS idx_itinerary_items_trip_id;
DROP INDEX IF EXISTS idx_itinerary_items_date;
DROP INDEX IF EXISTS idx_itinerary_items_type;

DROP INDEX IF EXISTS idx_search_parameters_trip_id;
DROP INDEX IF EXISTS idx_search_parameters_timestamp;

DROP INDEX IF EXISTS idx_price_history_entity_type;
DROP INDEX IF EXISTS idx_price_history_entity_id;
DROP INDEX IF EXISTS idx_price_history_timestamp;
DROP INDEX IF EXISTS idx_price_history_price;
DROP INDEX IF EXISTS idx_price_history_entity_combined;

DROP INDEX IF EXISTS idx_trip_notes_trip_id;
DROP INDEX IF EXISTS idx_trip_notes_timestamp;

DROP INDEX IF EXISTS idx_saved_options_trip_id;
DROP INDEX IF EXISTS idx_saved_options_option_type;
DROP INDEX IF EXISTS idx_saved_options_option_id;
DROP INDEX IF EXISTS idx_saved_options_timestamp;
DROP INDEX IF EXISTS idx_saved_options_option_combined;

DROP INDEX IF EXISTS idx_trip_comparison_trip_id;

DROP INDEX IF EXISTS idx_users_preferences_gin;
DROP INDEX IF EXISTS idx_trips_flexibility_gin;
DROP INDEX IF EXISTS idx_accommodations_amenities_gin;
DROP INDEX IF EXISTS idx_search_parameters_parameter_json_gin;
DROP INDEX IF EXISTS idx_trip_comparison_comparison_json_gin;

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS trip_comparison;
DROP TABLE IF EXISTS saved_options;
DROP TABLE IF EXISTS price_history;
DROP TABLE IF EXISTS trip_notes;
DROP TABLE IF EXISTS search_parameters;
DROP TABLE IF EXISTS itinerary_items;
DROP TABLE IF EXISTS transportation;
DROP TABLE IF EXISTS accommodations;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS users;

-- Drop triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_trips_updated_at ON trips;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Disable UUID extension if no longer needed
-- DROP EXTENSION IF EXISTS "uuid-ossp";