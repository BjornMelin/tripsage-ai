-- Migration: Remove BIGINT IDs and use UUID as primary key only
-- Date: 2025-06-15
-- Description: Simplify database schema to use UUID as the only primary key, removing all backwards compatibility

-- Begin transaction
BEGIN;

-- Step 1: Drop foreign key constraints that reference the BIGINT id
ALTER TABLE trip_notes DROP CONSTRAINT IF EXISTS trip_notes_trip_id_fkey;
ALTER TABLE trip_collaborators DROP CONSTRAINT IF EXISTS trip_collaborators_trip_id_fkey;
ALTER TABLE trip_comparisons DROP CONSTRAINT IF EXISTS trip_comparisons_trip_id_fkey;
ALTER TABLE trip_attachments DROP CONSTRAINT IF EXISTS trip_attachments_trip_id_fkey;
ALTER TABLE flights DROP CONSTRAINT IF EXISTS flights_trip_id_fkey;
ALTER TABLE accommodations DROP CONSTRAINT IF EXISTS accommodations_trip_id_fkey;
ALTER TABLE activities DROP CONSTRAINT IF EXISTS activities_trip_id_fkey;

-- Step 2: Ensure all trips have a UUID (in case any are missing)
UPDATE trips 
SET uuid_id = gen_random_uuid() 
WHERE uuid_id IS NULL;

-- Step 3: Update related tables to use UUID foreign keys
-- First, add new UUID columns if they don't exist
ALTER TABLE trip_notes ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE trip_collaborators ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE trip_comparisons ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE trip_attachments ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE accommodations ADD COLUMN IF NOT EXISTS trip_uuid UUID;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS trip_uuid UUID;

-- Update the UUID columns with the corresponding trip UUID
UPDATE trip_notes tn
SET trip_uuid = t.uuid_id
FROM trips t
WHERE tn.trip_id = t.id;

UPDATE trip_collaborators tc
SET trip_uuid = t.uuid_id
FROM trips t
WHERE tc.trip_id = t.id;

UPDATE trip_comparisons tc
SET trip_uuid = t.uuid_id
FROM trips t
WHERE tc.trip_id = t.id;

UPDATE trip_attachments ta
SET trip_uuid = t.uuid_id
FROM trips t
WHERE ta.trip_id = t.id;

UPDATE flights f
SET trip_uuid = t.uuid_id
FROM trips t
WHERE f.trip_id = t.id;

UPDATE accommodations a
SET trip_uuid = t.uuid_id
FROM trips t
WHERE a.trip_id = t.id;

UPDATE activities a
SET trip_uuid = t.uuid_id
FROM trips t
WHERE a.trip_id = t.id;

-- Step 4: Drop the old BIGINT id column from trips
ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_pkey;
ALTER TABLE trips DROP COLUMN IF EXISTS id;

-- Step 5: Rename uuid_id to id and make it primary key
ALTER TABLE trips RENAME COLUMN uuid_id TO id;
ALTER TABLE trips ADD PRIMARY KEY (id);

-- Step 6: Drop old BIGINT foreign key columns and rename UUID columns
ALTER TABLE trip_notes DROP COLUMN IF EXISTS trip_id;
ALTER TABLE trip_notes RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE trip_notes ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE trip_collaborators DROP COLUMN IF EXISTS trip_id;
ALTER TABLE trip_collaborators RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE trip_collaborators ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE trip_comparisons DROP COLUMN IF EXISTS trip_id;
ALTER TABLE trip_comparisons RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE trip_comparisons ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE trip_attachments DROP COLUMN IF EXISTS trip_id;
ALTER TABLE trip_attachments RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE trip_attachments ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE flights DROP COLUMN IF EXISTS trip_id;
ALTER TABLE flights RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE flights ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE accommodations DROP COLUMN IF EXISTS trip_id;
ALTER TABLE accommodations RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE accommodations ALTER COLUMN trip_id SET NOT NULL;

ALTER TABLE activities DROP COLUMN IF EXISTS trip_id;
ALTER TABLE activities RENAME COLUMN trip_uuid TO trip_id;
ALTER TABLE activities ALTER COLUMN trip_id SET NOT NULL;

-- Step 7: Add foreign key constraints back
ALTER TABLE trip_notes ADD CONSTRAINT trip_notes_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE trip_collaborators ADD CONSTRAINT trip_collaborators_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE trip_comparisons ADD CONSTRAINT trip_comparisons_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE trip_attachments ADD CONSTRAINT trip_attachments_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE flights ADD CONSTRAINT flights_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE accommodations ADD CONSTRAINT accommodations_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE activities ADD CONSTRAINT activities_trip_id_fkey 
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

-- Step 8: Remove legacy columns
ALTER TABLE trips DROP COLUMN IF EXISTS name; -- Using title instead
ALTER TABLE trips DROP COLUMN IF EXISTS flexibility; -- Using preferences_extended instead
ALTER TABLE trips DROP COLUMN IF EXISTS preferences; -- Using preferences_extended instead

-- Step 9: Ensure enhanced columns are not null with defaults
ALTER TABLE trips ALTER COLUMN visibility SET DEFAULT 'private';
ALTER TABLE trips ALTER COLUMN tags SET DEFAULT '{}';
ALTER TABLE trips ALTER COLUMN preferences_extended SET DEFAULT '{}';
ALTER TABLE trips ALTER COLUMN budget_breakdown SET DEFAULT '{"total": 0, "currency": "USD", "spent": 0, "breakdown": {}}';

-- Step 10: Add constraints for data integrity
ALTER TABLE trips ADD CONSTRAINT check_visibility 
    CHECK (visibility IN ('private', 'shared', 'public'));

ALTER TABLE trips ADD CONSTRAINT check_dates 
    CHECK (end_date >= start_date);

ALTER TABLE trips ADD CONSTRAINT check_travelers 
    CHECK (travelers > 0);

-- Step 11: Update users table to use UUID if not already
ALTER TABLE users ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT gen_random_uuid();
UPDATE users SET uuid_id = gen_random_uuid() WHERE uuid_id IS NULL;

-- Update user_id columns in trips to UUID
ALTER TABLE trips ADD COLUMN IF NOT EXISTS user_uuid UUID;
UPDATE trips t SET user_uuid = u.uuid_id FROM users u WHERE t.user_id = u.id::text;
ALTER TABLE trips DROP COLUMN IF EXISTS user_id;
ALTER TABLE trips RENAME COLUMN user_uuid TO user_id;
ALTER TABLE trips ALTER COLUMN user_id SET NOT NULL;

-- Step 12: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_visibility ON trips(visibility);
CREATE INDEX IF NOT EXISTS idx_trips_start_date ON trips(start_date);
CREATE INDEX IF NOT EXISTS idx_trips_tags ON trips USING gin(tags);

-- Commit transaction
COMMIT;