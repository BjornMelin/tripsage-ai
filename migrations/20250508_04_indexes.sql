-- Migration: Indexes
-- Description: Creates indexes for query optimization in the TripSage travel planning system
-- Created: 2025-05-08

-- Indexes for trips table
CREATE INDEX idx_trips_start_date ON trips (start_date);
CREATE INDEX idx_trips_end_date ON trips (end_date);
CREATE INDEX idx_trips_destination ON trips (destination);
CREATE INDEX idx_trips_status ON trips (status);
CREATE INDEX idx_trips_trip_type ON trips (trip_type);

-- Indexes for flights table
CREATE INDEX idx_flights_trip_id ON flights (trip_id);
CREATE INDEX idx_flights_origin ON flights (origin);
CREATE INDEX idx_flights_destination ON flights (destination);
CREATE INDEX idx_flights_departure_time ON flights (departure_time);
CREATE INDEX idx_flights_price ON flights (price);
CREATE INDEX idx_flights_booking_status ON flights (booking_status);
CREATE INDEX idx_flights_search_timestamp ON flights (search_timestamp);

-- Indexes for accommodations table
CREATE INDEX idx_accommodations_trip_id ON accommodations (trip_id);
CREATE INDEX idx_accommodations_location ON accommodations (location);
CREATE INDEX idx_accommodations_check_in ON accommodations (check_in);
CREATE INDEX idx_accommodations_check_out ON accommodations (check_out);
CREATE INDEX idx_accommodations_price_per_night ON accommodations (price_per_night);
CREATE INDEX idx_accommodations_total_price ON accommodations (total_price);
CREATE INDEX idx_accommodations_rating ON accommodations (rating);
CREATE INDEX idx_accommodations_booking_status ON accommodations (booking_status);
CREATE INDEX idx_accommodations_search_timestamp ON accommodations (search_timestamp);
CREATE INDEX idx_accommodations_type ON accommodations (type);

-- Indexes for transportation table
CREATE INDEX idx_transportation_trip_id ON transportation (trip_id);
CREATE INDEX idx_transportation_type ON transportation (type);
CREATE INDEX idx_transportation_pickup_date ON transportation (pickup_date);
CREATE INDEX idx_transportation_price ON transportation (price);
CREATE INDEX idx_transportation_booking_status ON transportation (booking_status);

-- Indexes for itinerary_items table
CREATE INDEX idx_itinerary_items_trip_id ON itinerary_items (trip_id);
CREATE INDEX idx_itinerary_items_date ON itinerary_items (date);
CREATE INDEX idx_itinerary_items_type ON itinerary_items (type);

-- Indexes for search_parameters table
CREATE INDEX idx_search_parameters_trip_id ON search_parameters (trip_id);
CREATE INDEX idx_search_parameters_timestamp ON search_parameters (timestamp);

-- Indexes for price_history table
CREATE INDEX idx_price_history_entity_type ON price_history (entity_type);
CREATE INDEX idx_price_history_entity_id ON price_history (entity_id);
CREATE INDEX idx_price_history_timestamp ON price_history (timestamp);
CREATE INDEX idx_price_history_price ON price_history (price);
CREATE INDEX idx_price_history_entity_combined ON price_history (entity_type, entity_id);

-- Indexes for trip_notes table
CREATE INDEX idx_trip_notes_trip_id ON trip_notes (trip_id);
CREATE INDEX idx_trip_notes_timestamp ON trip_notes (timestamp);

-- Indexes for saved_options table
CREATE INDEX idx_saved_options_trip_id ON saved_options (trip_id);
CREATE INDEX idx_saved_options_option_type ON saved_options (option_type);
CREATE INDEX idx_saved_options_option_id ON saved_options (option_id);
CREATE INDEX idx_saved_options_timestamp ON saved_options (timestamp);
CREATE INDEX idx_saved_options_option_combined ON saved_options (option_type, option_id);

-- Indexes for trip_comparison table
CREATE INDEX idx_trip_comparison_trip_id ON trip_comparison (trip_id);

-- GIN indexes for JSONB columns
CREATE INDEX idx_users_preferences_gin ON users USING GIN (preferences_json);
CREATE INDEX idx_trips_flexibility_gin ON trips USING GIN (flexibility);
CREATE INDEX idx_accommodations_amenities_gin ON accommodations USING GIN (amenities);
CREATE INDEX idx_search_parameters_parameter_json_gin ON search_parameters USING GIN (parameter_json);
CREATE INDEX idx_trip_comparison_comparison_json_gin ON trip_comparison USING GIN (comparison_json);