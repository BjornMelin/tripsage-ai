-- Migration: Complex Relationship Tables
-- Description: Creates tables with complex relationships for TripSage travel planning system
-- Created: 2025-05-08

-- Create price_history table
CREATE TABLE IF NOT EXISTS price_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    price NUMERIC NOT NULL,
    CONSTRAINT price_history_price_check CHECK (price >= 0),
    CONSTRAINT price_history_entity_type_check CHECK (entity_type IN ('flight', 'accommodation', 'transportation', 'activity'))
);

COMMENT ON TABLE price_history IS 'Historical price data for various entities';
COMMENT ON COLUMN price_history.id IS 'Unique identifier for the price history record';
COMMENT ON COLUMN price_history.entity_type IS 'Type of entity (flight, accommodation, transportation, activity)';
COMMENT ON COLUMN price_history.entity_id IS 'ID of the entity in its respective table';
COMMENT ON COLUMN price_history.timestamp IS 'When the price was recorded';
COMMENT ON COLUMN price_history.price IS 'Price amount in default currency';

-- Create saved_options table
CREATE TABLE IF NOT EXISTS saved_options (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    option_type TEXT NOT NULL,
    option_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    CONSTRAINT saved_options_option_type_check CHECK (option_type IN ('flight', 'accommodation', 'transportation', 'activity'))
);

COMMENT ON TABLE saved_options IS 'Saved travel options for comparison';
COMMENT ON COLUMN saved_options.id IS 'Unique identifier for the saved option';
COMMENT ON COLUMN saved_options.trip_id IS 'Reference to the associated trip';
COMMENT ON COLUMN saved_options.option_type IS 'Type of option (flight, accommodation, transportation, activity)';
COMMENT ON COLUMN saved_options.option_id IS 'ID of the option in its respective table';
COMMENT ON COLUMN saved_options.timestamp IS 'When the option was saved';
COMMENT ON COLUMN saved_options.notes IS 'Additional notes about the saved option';

-- Create composite constraints for unique combinations
ALTER TABLE price_history ADD CONSTRAINT price_history_entity_unique UNIQUE (entity_type, entity_id, timestamp);
ALTER TABLE saved_options ADD CONSTRAINT saved_options_option_unique UNIQUE (trip_id, option_type, option_id);