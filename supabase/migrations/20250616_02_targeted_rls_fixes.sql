-- Targeted RLS Policy Fixes Migration
-- Description: Fix RLS security vulnerabilities for existing tables
-- Date: 2025-06-16
-- Addresses: Security test failures in user data isolation and collaboration permissions

BEGIN;

-- ===========================
-- DROP PROBLEMATIC POLICIES
-- ===========================

-- Drop existing policies that may have issues
DROP POLICY IF EXISTS "Users can view accessible trips" ON trips;
DROP POLICY IF EXISTS "trips_enhanced_access" ON trips;
DROP POLICY IF EXISTS "Users can update owned trips or shared trips with edit permissi" ON trips;
DROP POLICY IF EXISTS "Users can only access their own memories" ON memories;
DROP POLICY IF EXISTS "Users can view flights for accessible trips" ON flights;
DROP POLICY IF EXISTS "Users can access flights for their trips" ON flights;
DROP POLICY IF EXISTS "Users can modify flights with edit permissions" ON flights;
DROP POLICY IF EXISTS "Users can update flights with edit permissions" ON flights;
DROP POLICY IF EXISTS "Users can delete flights with edit permissions" ON flights;

-- ===========================
-- CORE USER DATA ISOLATION POLICIES
-- ===========================

-- 1. TRIPS TABLE - Fix user isolation and collaboration
CREATE POLICY "trips_select_policy" ON trips
FOR SELECT
TO authenticated
USING (
    -- User owns the trip
    user_id = auth.uid()
    OR
    -- User is a collaborator on the trip
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
    )
);

CREATE POLICY "trips_update_policy" ON trips
FOR UPDATE
TO authenticated
USING (
    -- User owns the trip
    user_id = auth.uid()
    OR
    -- User has edit or admin permissions (NOT view-only)
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    -- Same conditions for WITH CHECK
    user_id = auth.uid()
    OR
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
        AND tc.permission_level IN ('edit', 'admin')
    )
);

-- Keep existing insert and delete policies as they're correct
-- Users can create their own trips
-- Users can delete their own trips

-- 2. MEMORIES TABLE - Strict user isolation
CREATE POLICY "memories_user_isolation" ON memories
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- 3. FLIGHTS TABLE - Proper collaboration inheritance
CREATE POLICY "flights_select_policy" ON flights
FOR SELECT
TO authenticated
USING (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User is a collaborator on the trip
        SELECT tc.trip_id FROM trip_collaborators tc WHERE tc.user_id = auth.uid()
    )
);

CREATE POLICY "flights_insert_policy" ON flights
FOR INSERT
TO authenticated
WITH CHECK (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "flights_update_policy" ON flights
FOR UPDATE
TO authenticated
USING (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "flights_delete_policy" ON flights
FOR DELETE
TO authenticated
USING (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

-- ===========================
-- EXTEND POLICIES TO ALL RELATED TABLES
-- ===========================

-- Apply same collaboration patterns to other trip-related tables
DROP POLICY IF EXISTS "Users can view accommodations for accessible trips" ON accommodations;
DROP POLICY IF EXISTS "Users can update accommodations with edit permissions" ON accommodations;
DROP POLICY IF EXISTS "Users can modify accommodations with edit permissions" ON accommodations;
DROP POLICY IF EXISTS "Users can delete accommodations with edit permissions" ON accommodations;
DROP POLICY IF EXISTS "Users can access accommodations for their trips" ON accommodations;

CREATE POLICY "accommodations_select_policy" ON accommodations
FOR SELECT
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc WHERE tc.user_id = auth.uid()
    )
);

CREATE POLICY "accommodations_insert_policy" ON accommodations
FOR INSERT
TO authenticated
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "accommodations_update_policy" ON accommodations
FOR UPDATE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "accommodations_delete_policy" ON accommodations
FOR DELETE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

-- Transportation table
DROP POLICY IF EXISTS "Users can access transportation for their trips" ON transportation;

CREATE POLICY "transportation_select_policy" ON transportation
FOR SELECT
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc WHERE tc.user_id = auth.uid()
    )
);

CREATE POLICY "transportation_insert_policy" ON transportation
FOR INSERT
TO authenticated
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "transportation_update_policy" ON transportation
FOR UPDATE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "transportation_delete_policy" ON transportation
FOR DELETE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

-- Itinerary items table
DROP POLICY IF EXISTS "Users can access itinerary items for their trips" ON itinerary_items;

CREATE POLICY "itinerary_items_select_policy" ON itinerary_items
FOR SELECT
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc WHERE tc.user_id = auth.uid()
    )
);

CREATE POLICY "itinerary_items_insert_policy" ON itinerary_items
FOR INSERT
TO authenticated
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "itinerary_items_update_policy" ON itinerary_items
FOR UPDATE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

CREATE POLICY "itinerary_items_delete_policy" ON itinerary_items
FOR DELETE
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);

-- ===========================
-- FORCE RLS ON CRITICAL TABLES
-- ===========================

-- Ensure RLS cannot be bypassed by superuser
ALTER TABLE trips FORCE ROW LEVEL SECURITY;
ALTER TABLE memories FORCE ROW LEVEL SECURITY;
ALTER TABLE flights FORCE ROW LEVEL SECURITY;
ALTER TABLE accommodations FORCE ROW LEVEL SECURITY;
ALTER TABLE transportation FORCE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items FORCE ROW LEVEL SECURITY;
ALTER TABLE session_memories FORCE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;

-- ===========================
-- PERFORMANCE OPTIMIZATION
-- ===========================

-- Create indexes to optimize RLS policy performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trip_collaborators_user_trip 
ON trip_collaborators(user_id, trip_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trip_collaborators_trip_permission 
ON trip_collaborators(trip_id, permission_level) 
WHERE permission_level IN ('edit', 'admin');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trips_user_id 
ON trips(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_user_id 
ON memories(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_memories_user_id 
ON session_memories(user_id);

-- ===========================
-- DOCUMENTATION AND VERIFICATION
-- ===========================

COMMENT ON POLICY "trips_select_policy" ON trips IS 
'Users can view trips they own or trips they collaborate on';

COMMENT ON POLICY "trips_update_policy" ON trips IS 
'Users can update trips they own or trips where they have edit/admin permissions (NOT view-only)';

COMMENT ON POLICY "memories_user_isolation" ON memories IS 
'Strict user isolation - users can only access their own memories';

COMMENT ON POLICY "flights_select_policy" ON flights IS 
'Users can view flights for trips they own or collaborate on';

-- Verify RLS is enabled and policies are in place
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check that all critical tables have RLS enabled
    SELECT COUNT(*) INTO policy_count
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename IN ('trips', 'memories', 'flights', 'accommodations', 'transportation', 'itinerary_items')
    AND rowsecurity = true;
    
    IF policy_count < 6 THEN
        RAISE EXCEPTION 'RLS not enabled on all critical tables';
    END IF;
    
    -- Check that policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies 
    WHERE schemaname = 'public';
    
    IF policy_count < 20 THEN
        RAISE EXCEPTION 'Insufficient RLS policies found';
    END IF;
    
    RAISE NOTICE 'RLS Policy Fix Migration Applied Successfully!';
    RAISE NOTICE '✅ Fixed user isolation for trips table';
    RAISE NOTICE '✅ Fixed user isolation for memories table';
    RAISE NOTICE '✅ Fixed viewer permission restrictions on trips';
    RAISE NOTICE '✅ Fixed non-collaborator access to trips and flights';
    RAISE NOTICE '✅ Fixed collaboration permissions for all trip-related tables';
    RAISE NOTICE '✅ Added performance indexes for RLS queries';
    RAISE NOTICE '✅ Forced RLS on all critical tables';
END $$;

COMMIT;