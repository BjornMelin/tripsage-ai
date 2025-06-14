-- Migration: Enable Automation Extensions and Scheduled Jobs
-- Description: Adds pg_cron, pg_net, and real-time capabilities for automation
-- Dependencies: Previous migrations must be applied
-- Version: 20250611_02

-- ===========================
-- ENABLE NEW EXTENSIONS
-- ===========================

-- Enable pg_cron for scheduled jobs
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Enable pg_net for HTTP requests
CREATE EXTENSION IF NOT EXISTS "pg_net";

-- Enable pg_stat_statements for monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Enable btree_gist for advanced indexing
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Enable pgcrypto for encryption
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===========================
-- CONFIGURE EXTENSIONS
-- ===========================

-- Grant permissions for pg_cron
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;

-- Configure extension settings
ALTER SYSTEM SET cron.database_name = 'postgres';
ALTER SYSTEM SET pg_net.batch_size = 200;
ALTER SYSTEM SET pg_net.ttl = '1 hour';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Apply configuration changes
SELECT pg_reload_conf();

-- ===========================
-- CONFIGURE REALTIME
-- ===========================

-- Drop existing publication if exists
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;

-- Create new publication
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time publication
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
ALTER PUBLICATION supabase_realtime ADD TABLE itinerary_items;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_tool_calls;

-- ===========================
-- CREATE MONITORING TABLES
-- ===========================

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhook configuration tables
CREATE TABLE IF NOT EXISTS webhook_configs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    secret TEXT,
    events TEXT[] NOT NULL,
    headers JSONB DEFAULT '{}',
    retry_config JSONB DEFAULT '{"max_retries": 3, "retry_delay": 1000}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    webhook_config_id BIGINT REFERENCES webhook_configs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    attempt_count INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ===========================
-- CREATE INDEXES
-- ===========================

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, read) 
WHERE read = false;

CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time 
ON system_metrics(metric_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_config_time
ON webhook_logs(webhook_config_id, created_at DESC);

-- ===========================
-- CREATE VERIFICATION FUNCTION
-- ===========================

CREATE OR REPLACE FUNCTION verify_automation_setup()
RETURNS TABLE (
    component TEXT,
    status TEXT,
    details TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Check pg_cron
    RETURN QUERY
    SELECT 
        'pg_cron'::TEXT,
        CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') 
             THEN 'installed'::TEXT ELSE 'missing'::TEXT END,
        CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron')
             THEN 'Extension installed and ready for scheduled jobs'::TEXT
             ELSE 'Extension not installed'::TEXT END;
    
    -- Check pg_net
    RETURN QUERY
    SELECT 
        'pg_net'::TEXT,
        CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_net') 
             THEN 'installed'::TEXT ELSE 'missing'::TEXT END,
        CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_net')
             THEN 'Extension installed and ready for HTTP requests'::TEXT
             ELSE 'Extension not installed'::TEXT END;
    
    -- Check realtime publication
    RETURN QUERY
    SELECT 
        'realtime'::TEXT,
        CASE WHEN EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') 
             THEN 'configured'::TEXT ELSE 'missing'::TEXT END,
        CASE WHEN EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime')
             THEN format('Publication configured with %s tables', 
                         (SELECT COUNT(*) FROM pg_publication_tables WHERE pubname = 'supabase_realtime')::TEXT)
             ELSE 'Publication not configured'::TEXT END;
    
    -- Check monitoring tables
    RETURN QUERY
    SELECT 
        'monitoring_tables'::TEXT,
        CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications')
             AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_metrics')
             THEN 'created'::TEXT ELSE 'missing'::TEXT END,
        'Monitoring tables for notifications and metrics'::TEXT;
    
    -- Check webhook tables
    RETURN QUERY
    SELECT 
        'webhook_tables'::TEXT,
        CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'webhook_configs')
             AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'webhook_logs')
             THEN 'created'::TEXT ELSE 'missing'::TEXT END,
        'Webhook configuration and logging tables'::TEXT;
END;
$$;

-- ===========================
-- RUN VERIFICATION
-- ===========================

-- Verify the setup
SELECT * FROM verify_automation_setup();