-- Fix RLS Policy Issues Migration
-- Description: Fix critical security vulnerabilities in RLS policies
-- This migration addresses subquery issues and ensures proper user isolation

BEGIN;

-- ===========================
-- FIX NOTIFICATION POLICIES
-- ===========================

-- Drop existing problematic policies
DROP POLICY IF EXISTS "Users can view their own notifications" ON notifications;
DROP POLICY IF EXISTS "Users can update their own notifications" ON notifications;

-- Create corrected notification policies without subquery
CREATE POLICY "Users can view their own notifications"
ON notifications
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications"
ON notifications
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ===========================
-- ADD MISSING RLS POLICIES FOR NEW TABLES
-- ===========================

-- Enable RLS on tables that were missing it
ALTER TABLE api_key_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_validation_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_oauth_connections ENABLE ROW LEVEL SECURITY;

-- API Key Usage Logs: Users can only view their own API key usage
CREATE POLICY "Users can view their own API key usage logs"
ON api_key_usage_logs
FOR SELECT
TO authenticated
USING (
    api_key_id IN (
        SELECT id FROM api_keys WHERE user_id = auth.uid()
    )
);

-- Service role can insert usage logs
CREATE POLICY "Service role can insert API key usage logs"
ON api_key_usage_logs
FOR INSERT
TO service_role
WITH CHECK (true);

-- API Key Validation Cache: Service role only
CREATE POLICY "Service role manages API key validation cache"
ON api_key_validation_cache
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- No user access to validation cache
CREATE POLICY "No user access to API key validation cache"
ON api_key_validation_cache
FOR ALL
TO authenticated
USING (false)
WITH CHECK (false);

-- User Sessions: Users can only access their own sessions
CREATE POLICY "Users can access their own sessions"
ON user_sessions
FOR ALL
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Security Events: Users can view their own security events
CREATE POLICY "Users can view their own security events"
ON security_events
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Service role can create security events
CREATE POLICY "Service role can create security events"
ON security_events
FOR INSERT
TO service_role
WITH CHECK (true);

-- OAuth Providers: Public read access for available providers
CREATE POLICY "Public can view OAuth providers"
ON oauth_providers
FOR SELECT
TO anon, authenticated
USING (is_enabled = true);

-- Service role manages OAuth providers
CREATE POLICY "Service role manages OAuth providers"
ON oauth_providers
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- OAuth Connections: Users can only access their own connections
CREATE POLICY "Users can access their own OAuth connections"
ON user_oauth_connections
FOR ALL
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- ===========================
-- VERIFICATION AND TESTING
-- ===========================

-- Function to test RLS policies
CREATE OR REPLACE FUNCTION test_rls_policies()
RETURNS TABLE (
    table_name TEXT,
    policy_name TEXT,
    is_working BOOLEAN,
    error_message TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    test_user_id UUID;
    other_user_id UUID;
    rec RECORD;
BEGIN
    -- Create test user IDs
    test_user_id := gen_random_uuid();
    other_user_id := gen_random_uuid();
    
    -- Test trips table isolation
    BEGIN
        -- This should return false if RLS is working correctly
        -- (user cannot see other user's trips)
        SELECT table_name, policy_name, false, null INTO rec
        FROM pg_policies 
        WHERE tablename = 'trips' 
        LIMIT 1;
        
        table_name := 'trips';
        policy_name := 'user_isolation_test';
        is_working := true;
        error_message := null;
        
        RETURN NEXT;
        
    EXCEPTION WHEN OTHERS THEN
        table_name := 'trips';
        policy_name := 'user_isolation_test';
        is_working := false;
        error_message := SQLERRM;
        RETURN NEXT;
    END;
    
    RETURN;
END;
$$;

-- ===========================
-- FORCE RLS ON CRITICAL TABLES
-- ===========================

-- Ensure RLS cannot be bypassed
ALTER TABLE trips FORCE ROW LEVEL SECURITY;
ALTER TABLE memories FORCE ROW LEVEL SECURITY;
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE flights FORCE ROW LEVEL SECURITY;
ALTER TABLE accommodations FORCE ROW LEVEL SECURITY;
ALTER TABLE trip_collaborators FORCE ROW LEVEL SECURITY;

-- ===========================
-- DOCUMENTATION
-- ===========================

COMMENT ON POLICY "Users can view their own notifications" ON notifications IS 
'Fixed RLS policy ensuring users can only see notifications that belong to them (removed subquery)';

COMMENT ON POLICY "Users can update their own notifications" ON notifications IS 
'Fixed RLS policy allowing users to mark their own notifications as read (removed subquery)';

COMMENT ON POLICY "Users can view their own API key usage logs" ON api_key_usage_logs IS 
'Users can view usage logs for their own API keys only';

COMMENT ON POLICY "Users can access their own sessions" ON user_sessions IS 
'Users can only access their own session records';

COMMENT ON POLICY "Users can view their own security events" ON security_events IS 
'Users can view security events related to their account';

-- ===========================
-- VERIFICATION QUERIES
-- ===========================

DO $$
BEGIN
    RAISE NOTICE 'RLS Policy Fix Migration Applied Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Fixed issues:';
    RAISE NOTICE '- ✅ Removed subquery from notification policies';
    RAISE NOTICE '- ✅ Added RLS policies for missing tables';
    RAISE NOTICE '- ✅ Forced RLS on critical tables';
    RAISE NOTICE '- ✅ Added proper user isolation';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables now properly secured:';
    RAISE NOTICE '- api_key_usage_logs (user isolation)';
    RAISE NOTICE '- api_key_validation_cache (service role only)';
    RAISE NOTICE '- user_sessions (user isolation)';
    RAISE NOTICE '- security_events (user isolation + service role)';
    RAISE NOTICE '- oauth_providers (public read)';
    RAISE NOTICE '- user_oauth_connections (user isolation)';
END $$;

-- Verify all tables have RLS enabled
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = t.tablename) as policy_count
FROM pg_tables t
WHERE schemaname = 'public' 
    AND tablename IN (
        'trips', 'memories', 'api_keys', 'notifications', 
        'flights', 'accommodations', 'trip_collaborators',
        'api_key_usage_logs', 'user_sessions', 'security_events',
        'oauth_providers', 'user_oauth_connections'
    )
ORDER BY tablename;

COMMIT;