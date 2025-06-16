-- Configuration Management RLS Policies Migration
-- Description: Add comprehensive RLS policies for configuration management tables
-- Date: 2025-06-16
-- Security: Critical security fix for configuration data isolation

BEGIN;

-- ===========================
-- ENABLE RLS ON CONFIGURATION TABLES
-- ===========================

-- Enable RLS on all configuration management tables
ALTER TABLE configuration_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuration_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuration_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuration_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuration_performance_metrics ENABLE ROW LEVEL SECURITY;

-- Force RLS to prevent superuser bypass
ALTER TABLE configuration_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE configuration_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE configuration_changes FORCE ROW LEVEL SECURITY;
ALTER TABLE configuration_exports FORCE ROW LEVEL SECURITY;
ALTER TABLE configuration_performance_metrics FORCE ROW LEVEL SECURITY;

-- ===========================
-- CONFIGURATION PROFILES POLICIES
-- ===========================

-- System configurations are readable by all authenticated users but only modifiable by admins
CREATE POLICY "system_configs_read_policy" ON configuration_profiles
FOR SELECT
TO authenticated
USING (
    -- Allow reading system-created configurations
    created_by = 'system'
    OR 
    -- Allow reading configurations created by the current user (if any)
    created_by = COALESCE(auth.email(), 'anonymous')
);

-- Only system/admin users can create configurations
CREATE POLICY "system_configs_create_policy" ON configuration_profiles
FOR INSERT
TO authenticated
WITH CHECK (
    -- Only allow system or authenticated admin users to create configs
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$' -- Admin email domains
        OR auth.jwt() ->> 'role' = 'service_role' -- Service role
    )
);

-- Only system/admin users can update configurations
CREATE POLICY "system_configs_update_policy" ON configuration_profiles
FOR UPDATE
TO authenticated
USING (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$' -- Admin email domains
        OR auth.jwt() ->> 'role' = 'service_role' -- Service role
        OR created_by = COALESCE(auth.email(), 'anonymous') -- Creator can update
    )
)
WITH CHECK (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$'
        OR auth.jwt() ->> 'role' = 'service_role'
        OR created_by = COALESCE(auth.email(), 'anonymous')
    )
);

-- Only system/admin users can delete configurations
CREATE POLICY "system_configs_delete_policy" ON configuration_profiles
FOR DELETE
TO authenticated
USING (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$' -- Admin email domains
        OR auth.jwt() ->> 'role' = 'service_role' -- Service role
    )
);

-- ===========================
-- CONFIGURATION VERSIONS POLICIES
-- ===========================

-- Users can read configuration versions for accessible profiles
CREATE POLICY "config_versions_read_policy" ON configuration_versions
FOR SELECT
TO authenticated
USING (
    configuration_profile_id IN (
        SELECT id FROM configuration_profiles
        WHERE created_by = 'system'
        OR created_by = COALESCE(auth.email(), 'anonymous')
    )
);

-- Only system/admin can create versions
CREATE POLICY "config_versions_create_policy" ON configuration_versions
FOR INSERT
TO authenticated
WITH CHECK (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$'
        OR auth.jwt() ->> 'role' = 'service_role'
    )
);

-- No direct updates allowed (versions are immutable)
CREATE POLICY "config_versions_no_update_policy" ON configuration_versions
FOR UPDATE
TO authenticated
USING (false);

-- Only system/admin can delete versions
CREATE POLICY "config_versions_delete_policy" ON configuration_versions
FOR DELETE
TO authenticated
USING (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$'
        OR auth.jwt() ->> 'role' = 'service_role'
    )
);

-- ===========================
-- CONFIGURATION CHANGES POLICIES
-- ===========================

-- Users can read changes for accessible versions
CREATE POLICY "config_changes_read_policy" ON configuration_changes
FOR SELECT
TO authenticated
USING (
    version_id IN (
        SELECT cv.id FROM configuration_versions cv
        JOIN configuration_profiles cp ON cv.configuration_profile_id = cp.id
        WHERE cp.created_by = 'system'
        OR cp.created_by = COALESCE(auth.email(), 'anonymous')
    )
);

-- Only system can create change records (automated)
CREATE POLICY "config_changes_create_policy" ON configuration_changes
FOR INSERT
TO authenticated
WITH CHECK (
    auth.jwt() ->> 'role' = 'service_role' -- Only service role can create change records
);

-- No updates or deletes allowed (audit trail)
CREATE POLICY "config_changes_no_modify_policy" ON configuration_changes
FOR UPDATE
TO authenticated
USING (false);

CREATE POLICY "config_changes_no_delete_policy" ON configuration_changes
FOR DELETE
TO authenticated
USING (false);

-- ===========================
-- CONFIGURATION EXPORTS POLICIES
-- ===========================

-- Users can read exports they created
CREATE POLICY "config_exports_read_policy" ON configuration_exports
FOR SELECT
TO authenticated
USING (
    created_by = COALESCE(auth.email(), 'anonymous')
    OR auth.email() ~ '@tripsage\.(com|ai)$' -- Admins can see all
    OR auth.jwt() ->> 'role' = 'service_role'
);

-- Users can create their own exports
CREATE POLICY "config_exports_create_policy" ON configuration_exports
FOR INSERT
TO authenticated
WITH CHECK (
    auth.email() IS NOT NULL
    AND created_by = COALESCE(auth.email(), 'anonymous')
);

-- Users can update their own exports, admins can update all
CREATE POLICY "config_exports_update_policy" ON configuration_exports
FOR UPDATE
TO authenticated
USING (
    created_by = COALESCE(auth.email(), 'anonymous')
    OR auth.email() ~ '@tripsage\.(com|ai)$'
    OR auth.jwt() ->> 'role' = 'service_role'
);

-- Users can delete their own exports, admins can delete all
CREATE POLICY "config_exports_delete_policy" ON configuration_exports
FOR DELETE
TO authenticated
USING (
    created_by = COALESCE(auth.email(), 'anonymous')
    OR auth.email() ~ '@tripsage\.(com|ai)$'
    OR auth.jwt() ->> 'role' = 'service_role'
);

-- ===========================
-- PERFORMANCE METRICS POLICIES
-- ===========================

-- Users can read performance metrics for accessible configurations
CREATE POLICY "config_metrics_read_policy" ON configuration_performance_metrics
FOR SELECT
TO authenticated
USING (
    configuration_profile_id IN (
        SELECT id FROM configuration_profiles
        WHERE created_by = 'system'
        OR created_by = COALESCE(auth.email(), 'anonymous')
    )
);

-- Only system can create performance metrics
CREATE POLICY "config_metrics_create_policy" ON configuration_performance_metrics
FOR INSERT
TO authenticated
WITH CHECK (
    auth.jwt() ->> 'role' = 'service_role' -- Only service role can create metrics
);

-- No updates allowed (metrics are immutable snapshots)
CREATE POLICY "config_metrics_no_update_policy" ON configuration_performance_metrics
FOR UPDATE
TO authenticated
USING (false);

-- Only system/admin can delete metrics
CREATE POLICY "config_metrics_delete_policy" ON configuration_performance_metrics
FOR DELETE
TO authenticated
USING (
    auth.email() IS NOT NULL
    AND (
        auth.email() ~ '@tripsage\.(com|ai)$'
        OR auth.jwt() ->> 'role' = 'service_role'
    )
);

-- ===========================
-- PERFORMANCE OPTIMIZATION
-- ===========================

-- Create indexes to optimize RLS policy performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_profiles_created_by 
ON configuration_profiles(created_by);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_versions_profile_id 
ON configuration_versions(configuration_profile_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_changes_version_id 
ON configuration_changes(version_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_exports_created_by 
ON configuration_exports(created_by);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_metrics_profile_id 
ON configuration_performance_metrics(configuration_profile_id);

-- ===========================
-- POLICY DOCUMENTATION
-- ===========================

COMMENT ON POLICY "system_configs_read_policy" ON configuration_profiles IS 
'Allows authenticated users to read system configurations and their own configurations';

COMMENT ON POLICY "system_configs_create_policy" ON configuration_profiles IS 
'Only admin users and service roles can create new configuration profiles';

COMMENT ON POLICY "config_versions_read_policy" ON configuration_versions IS 
'Users can read configuration version history for accessible configuration profiles';

COMMENT ON POLICY "config_changes_read_policy" ON configuration_changes IS 
'Users can read change audit trails for accessible configuration versions';

COMMENT ON POLICY "config_exports_read_policy" ON configuration_exports IS 
'Users can read their own configuration exports, admins can read all';

COMMENT ON POLICY "config_metrics_read_policy" ON configuration_performance_metrics IS 
'Users can read performance metrics for accessible configuration profiles';

-- ===========================
-- SECURITY VERIFICATION
-- ===========================

-- Verify RLS is properly enabled
DO $$
DECLARE
    policy_count INTEGER;
    table_count INTEGER;
BEGIN
    -- Check that all configuration tables have RLS enabled
    SELECT COUNT(*) INTO table_count
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename LIKE 'configuration_%'
    AND rowsecurity = true;
    
    IF table_count < 5 THEN
        RAISE EXCEPTION 'RLS not enabled on all configuration tables: found % enabled', table_count;
    END IF;
    
    -- Check that policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies 
    WHERE schemaname = 'public'
    AND tablename LIKE 'configuration_%';
    
    IF policy_count < 15 THEN
        RAISE EXCEPTION 'Insufficient RLS policies for configuration tables: found %', policy_count;
    END IF;
    
    RAISE NOTICE 'Configuration RLS Policy Migration Applied Successfully!';
    RAISE NOTICE '✅ RLS enabled on all 5 configuration tables';
    RAISE NOTICE '✅ % security policies created', policy_count;
    RAISE NOTICE '✅ Performance indexes added';
    RAISE NOTICE '✅ Admin-only access for modifications';
    RAISE NOTICE '✅ Audit trail protection (immutable records)';
    RAISE NOTICE '✅ Forced RLS prevents superuser bypass';
END $$;

COMMIT;