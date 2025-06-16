-- Configuration Management Schema Migration
-- Adds tables for agent configuration management with versioning and audit support
-- Date: 2025-06-16

-- Create configuration_profiles table for storing agent configurations
CREATE TABLE IF NOT EXISTS configuration_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN ('budget_agent', 'destination_research_agent', 'itinerary_agent')),
    scope VARCHAR(20) NOT NULL DEFAULT 'agent_specific' CHECK (scope IN ('global', 'environment', 'agent_specific', 'user_override')),
    
    -- Configuration fields
    temperature DECIMAL(3,2) NOT NULL DEFAULT 0.7 CHECK (temperature >= 0.0 AND temperature <= 2.0),
    max_tokens INTEGER NOT NULL DEFAULT 1000 CHECK (max_tokens >= 1 AND max_tokens <= 8000),
    top_p DECIMAL(3,2) NOT NULL DEFAULT 0.9 CHECK (top_p >= 0.0 AND top_p <= 1.0),
    timeout_seconds INTEGER NOT NULL DEFAULT 30 CHECK (timeout_seconds >= 5 AND timeout_seconds <= 300),
    model VARCHAR(50) NOT NULL DEFAULT 'gpt-4',
    
    -- Metadata
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    environment VARCHAR(20) NOT NULL DEFAULT 'development' CHECK (environment IN ('development', 'production', 'test', 'testing')),
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Ensure only one active config per agent type per environment
    CONSTRAINT unique_active_agent_config UNIQUE (agent_type, environment, is_active) 
        DEFERRABLE INITIALLY DEFERRED
);

-- Create partial unique index for active configurations
CREATE UNIQUE INDEX IF NOT EXISTS idx_config_profiles_active_agent_env 
ON configuration_profiles (agent_type, environment) 
WHERE is_active = true;

-- Create configuration_versions table for version history
CREATE TABLE IF NOT EXISTS configuration_versions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version_id VARCHAR(50) NOT NULL UNIQUE,
    configuration_profile_id UUID NOT NULL REFERENCES configuration_profiles(id) ON DELETE CASCADE,
    
    -- Snapshot of configuration at this version
    config_snapshot JSONB NOT NULL,
    
    -- Version metadata
    description TEXT,
    change_summary TEXT,
    is_current BOOLEAN NOT NULL DEFAULT false,
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    -- Performance tracking
    performance_metrics JSONB DEFAULT '{}'::jsonb
);

-- Create index for version queries
CREATE INDEX IF NOT EXISTS idx_config_versions_profile_created 
ON configuration_versions (configuration_profile_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_config_versions_current 
ON configuration_versions (configuration_profile_id) 
WHERE is_current = true;

-- Create configuration_changes table for detailed change tracking
CREATE TABLE IF NOT EXISTS configuration_changes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version_id UUID NOT NULL REFERENCES configuration_versions(id) ON DELETE CASCADE,
    
    -- Change details
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('added', 'modified', 'removed')),
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for change queries
CREATE INDEX IF NOT EXISTS idx_config_changes_version_field 
ON configuration_changes (version_id, field_name);

-- Create configuration_exports table for import/export functionality
CREATE TABLE IF NOT EXISTS configuration_exports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    export_id VARCHAR(50) NOT NULL UNIQUE,
    
    -- Export metadata
    source_environment VARCHAR(20) NOT NULL,
    export_data JSONB NOT NULL,
    format VARCHAR(20) NOT NULL DEFAULT 'json',
    description TEXT,
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    -- Optional expiration
    expires_at TIMESTAMPTZ
);

-- Create performance_metrics table for configuration optimization
CREATE TABLE IF NOT EXISTS configuration_performance_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    configuration_profile_id UUID NOT NULL REFERENCES configuration_profiles(id) ON DELETE CASCADE,
    
    -- Performance data
    average_response_time DECIMAL(10,3) NOT NULL,
    success_rate DECIMAL(5,4) NOT NULL CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    error_rate DECIMAL(5,4) NOT NULL CHECK (error_rate >= 0.0 AND error_rate <= 1.0),
    token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    cost_estimate DECIMAL(10,6) NOT NULL DEFAULT 0.0,
    
    -- Measurement metadata
    sample_size INTEGER NOT NULL DEFAULT 0,
    measurement_period_start TIMESTAMPTZ NOT NULL,
    measurement_period_end TIMESTAMPTZ NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for performance metrics queries
CREATE INDEX IF NOT EXISTS idx_perf_metrics_profile_measured 
ON configuration_performance_metrics (configuration_profile_id, measured_at DESC);

-- Create functions for configuration management

-- Function to create a new configuration version
CREATE OR REPLACE FUNCTION create_configuration_version(
    p_profile_id UUID,
    p_created_by VARCHAR(100),
    p_description TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_version_id VARCHAR(50);
    v_config_snapshot JSONB;
    v_new_version_uuid UUID;
BEGIN
    -- Generate version ID
    v_version_id := 'v' || EXTRACT(EPOCH FROM NOW())::TEXT || '_' || SUBSTRING(gen_random_uuid()::TEXT, 1, 8);
    
    -- Get current configuration snapshot
    SELECT jsonb_build_object(
        'agent_type', agent_type,
        'temperature', temperature,
        'max_tokens', max_tokens,
        'top_p', top_p,
        'timeout_seconds', timeout_seconds,
        'model', model,
        'scope', scope,
        'environment', environment
    ) INTO v_config_snapshot
    FROM configuration_profiles
    WHERE id = p_profile_id;
    
    -- Insert new version
    INSERT INTO configuration_versions (
        version_id, 
        configuration_profile_id, 
        config_snapshot, 
        description, 
        is_current, 
        created_by
    ) VALUES (
        v_version_id, 
        p_profile_id, 
        v_config_snapshot, 
        p_description, 
        true, 
        p_created_by
    ) RETURNING id INTO v_new_version_uuid;
    
    -- Mark previous versions as not current
    UPDATE configuration_versions 
    SET is_current = false 
    WHERE configuration_profile_id = p_profile_id 
      AND id != v_new_version_uuid;
    
    RETURN v_new_version_uuid;
END;
$$ LANGUAGE plpgsql;

-- Function to update configuration profile timestamp
CREATE OR REPLACE FUNCTION update_configuration_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS trg_config_profiles_updated_at ON configuration_profiles;
CREATE TRIGGER trg_config_profiles_updated_at
    BEFORE UPDATE ON configuration_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_configuration_timestamp();

-- Function to automatically create version on configuration change
CREATE OR REPLACE FUNCTION auto_create_config_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create version if meaningful fields changed
    IF (OLD.temperature != NEW.temperature OR 
        OLD.max_tokens != NEW.max_tokens OR 
        OLD.top_p != NEW.top_p OR 
        OLD.timeout_seconds != NEW.timeout_seconds OR 
        OLD.model != NEW.model) THEN
        
        PERFORM create_configuration_version(
            NEW.id, 
            NEW.updated_by, 
            'Auto-created on configuration update'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic version creation
DROP TRIGGER IF EXISTS trg_auto_config_version ON configuration_profiles;
CREATE TRIGGER trg_auto_config_version
    AFTER UPDATE ON configuration_profiles
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_config_version();

-- Insert default agent configurations
INSERT INTO configuration_profiles (
    agent_type, scope, temperature, max_tokens, top_p, timeout_seconds, model, 
    description, environment, created_by
) VALUES 
(
    'budget_agent', 'agent_specific', 0.2, 1000, 0.9, 30, 'gpt-4',
    'Budget optimization agent - low creativity, high accuracy', 'development', 'system'
),
(
    'destination_research_agent', 'agent_specific', 0.5, 1000, 0.9, 30, 'gpt-4',
    'Destination research agent - moderate creativity for comprehensive research', 'development', 'system'
),
(
    'itinerary_agent', 'agent_specific', 0.4, 1000, 0.9, 30, 'gpt-4',
    'Itinerary planning agent - structured creativity for logical planning', 'development', 'system'
)
ON CONFLICT (agent_type, environment, is_active) DO NOTHING;

-- Create production configurations
INSERT INTO configuration_profiles (
    agent_type, scope, temperature, max_tokens, top_p, timeout_seconds, model, 
    description, environment, created_by
) VALUES 
(
    'budget_agent', 'agent_specific', 0.1, 800, 0.8, 25, 'gpt-4',
    'Production budget agent - conservative settings for consistency', 'production', 'system'
),
(
    'destination_research_agent', 'agent_specific', 0.3, 800, 0.8, 25, 'gpt-4',
    'Production research agent - conservative creativity for reliable research', 'production', 'system'
),
(
    'itinerary_agent', 'agent_specific', 0.2, 800, 0.8, 25, 'gpt-4',
    'Production itinerary agent - conservative settings for reliable planning', 'production', 'system'
)
ON CONFLICT (agent_type, environment, is_active) DO NOTHING;

-- Create initial versions for all configurations
DO $$
DECLARE
    config_record RECORD;
BEGIN
    FOR config_record IN 
        SELECT id FROM configuration_profiles WHERE is_active = true
    LOOP
        PERFORM create_configuration_version(
            config_record.id, 
            'system', 
            'Initial configuration version'
        );
    END LOOP;
END $$;

-- Add helpful views for common queries

-- View for current active configurations
CREATE OR REPLACE VIEW active_agent_configurations AS
SELECT 
    cp.id,
    cp.agent_type,
    cp.temperature,
    cp.max_tokens,
    cp.top_p,
    cp.timeout_seconds,
    cp.model,
    cp.environment,
    cp.description,
    cp.created_at,
    cp.updated_at,
    cp.updated_by,
    cv.version_id as current_version
FROM configuration_profiles cp
LEFT JOIN configuration_versions cv ON cp.id = cv.configuration_profile_id AND cv.is_current = true
WHERE cp.is_active = true;

-- View for configuration history with performance metrics
CREATE OR REPLACE VIEW configuration_history AS
SELECT 
    cv.version_id,
    cp.agent_type,
    cp.environment,
    cv.config_snapshot,
    cv.description,
    cv.created_at,
    cv.created_by,
    cv.is_current,
    pm.average_response_time,
    pm.success_rate,
    pm.cost_estimate
FROM configuration_versions cv
JOIN configuration_profiles cp ON cv.configuration_profile_id = cp.id
LEFT JOIN configuration_performance_metrics pm ON cp.id = pm.configuration_profile_id
ORDER BY cv.created_at DESC;

-- Grant appropriate permissions (adjust as needed for your security model)
-- GRANT SELECT, INSERT, UPDATE ON configuration_profiles TO app_user;
-- GRANT SELECT, INSERT ON configuration_versions TO app_user;
-- GRANT SELECT, INSERT ON configuration_changes TO app_user;
-- GRANT SELECT, INSERT ON configuration_exports TO app_user;
-- GRANT SELECT, INSERT ON configuration_performance_metrics TO app_user;
-- GRANT SELECT ON active_agent_configurations TO app_user;
-- GRANT SELECT ON configuration_history TO app_user;

-- Add comments for documentation
COMMENT ON TABLE configuration_profiles IS 'Stores agent configuration profiles with versioning support';
COMMENT ON TABLE configuration_versions IS 'Tracks configuration version history with snapshots';
COMMENT ON TABLE configuration_changes IS 'Detailed change tracking for configuration auditing';
COMMENT ON TABLE configuration_exports IS 'Configuration export/import data storage';
COMMENT ON TABLE configuration_performance_metrics IS 'Performance metrics for configuration optimization';

COMMENT ON FUNCTION create_configuration_version IS 'Creates a new configuration version with automatic snapshot';
COMMENT ON VIEW active_agent_configurations IS 'Current active configurations for all agents by environment';
COMMENT ON VIEW configuration_history IS 'Complete configuration history with performance data';