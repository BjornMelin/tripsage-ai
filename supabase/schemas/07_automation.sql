-- Automated Maintenance and Scheduled Jobs
-- Description: pg_cron scheduled jobs for automated database maintenance
-- Dependencies: 00_extensions.sql (pg_cron), 01_tables.sql, 03_functions.sql

-- ===========================
-- CLEANUP JOBS
-- ===========================

-- Remove expired cache entries daily
SELECT cron.schedule(
    'cleanup-expired-search-cache',
    '0 2 * * *', -- Run at 2 AM daily
    $$
    DELETE FROM search_destinations WHERE expires_at < NOW();
    DELETE FROM search_activities WHERE expires_at < NOW();
    DELETE FROM search_flights WHERE expires_at < NOW();
    DELETE FROM search_hotels WHERE expires_at < NOW();
    $$
);

-- Clean up old session memories (older than 30 days)
SELECT cron.schedule(
    'cleanup-old-session-memories',
    '0 3 * * *', -- Run at 3 AM daily
    $$
    DELETE FROM session_memories 
    WHERE created_at < NOW() - INTERVAL '30 days';
    $$
);

-- Archive completed trips older than 1 year
SELECT cron.schedule(
    'archive-old-completed-trips',
    '0 4 * * 0', -- Run at 4 AM every Sunday
    $$
    UPDATE trips 
    SET status = 'archived'
    WHERE status = 'completed' 
    AND updated_at < NOW() - INTERVAL '1 year';
    $$
);

-- ===========================
-- PERFORMANCE OPTIMIZATION JOBS
-- ===========================

-- Update table statistics for query optimization
SELECT cron.schedule(
    'update-table-statistics',
    '0 1 * * *', -- Run at 1 AM daily
    $$
    ANALYZE trips;
    ANALYZE flights;
    ANALYZE accommodations;
    ANALYZE chat_messages;
    ANALYZE memories;
    ANALYZE search_destinations;
    ANALYZE search_activities;
    ANALYZE search_flights;
    ANALYZE search_hotels;
    $$
);

-- Vacuum tables to reclaim storage
SELECT cron.schedule(
    'vacuum-tables',
    '0 5 * * 0', -- Run at 5 AM every Sunday
    $$
    VACUUM ANALYZE trips;
    VACUUM ANALYZE flights;
    VACUUM ANALYZE accommodations;
    VACUUM ANALYZE chat_messages;
    VACUUM ANALYZE memories;
    $$
);

-- ===========================
-- MONITORING JOBS
-- ===========================

-- Monitor API key usage and send alerts for expiring keys
SELECT cron.schedule(
    'monitor-expiring-api-keys',
    '0 9 * * *', -- Run at 9 AM daily
    $$
    INSERT INTO notifications (user_id, type, title, message, metadata)
    SELECT 
        user_id,
        'api_key_expiring',
        'API Key Expiring Soon',
        format('Your %s API key "%s" will expire in %s days', 
               service_name, key_name, 
               EXTRACT(DAY FROM expires_at - NOW())::TEXT),
        jsonb_build_object(
            'service_name', service_name,
            'key_name', key_name,
            'expires_at', expires_at
        )
    FROM api_keys
    WHERE is_active = true
    AND expires_at IS NOT NULL
    AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'
    AND NOT EXISTS (
        SELECT 1 FROM notifications n
        WHERE n.user_id = api_keys.user_id
        AND n.type = 'api_key_expiring'
        AND n.metadata->>'service_name' = api_keys.service_name
        AND n.metadata->>'key_name' = api_keys.key_name
        AND n.created_at > NOW() - INTERVAL '7 days'
    );
    $$
);

-- ===========================
-- WEBHOOK NOTIFICATION FUNCTIONS
-- ===========================

-- Function to send webhook notifications using pg_net
CREATE OR REPLACE FUNCTION send_webhook_notification(
    webhook_url TEXT,
    event_type TEXT,
    payload JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    request_id BIGINT;
BEGIN
    SELECT net.http_post(
        url := webhook_url,
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Event-Type', event_type,
            'X-Timestamp', EXTRACT(EPOCH FROM NOW())::TEXT
        ),
        body := payload::TEXT
    ) INTO request_id;
    
    RETURN request_id;
END;
$$;

-- Function to notify Edge Functions of trip updates
CREATE OR REPLACE FUNCTION notify_trip_update()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    edge_function_url TEXT;
    notification_payload JSONB;
BEGIN
    -- Get Edge Function URL from environment or config
    edge_function_url := current_setting('app.edge_function_url', true);
    
    IF edge_function_url IS NOT NULL THEN
        notification_payload := jsonb_build_object(
            'event', TG_OP,
            'table', TG_TABLE_NAME,
            'trip_id', NEW.id,
            'user_id', NEW.user_id,
            'timestamp', NOW(),
            'changes', CASE 
                WHEN TG_OP = 'UPDATE' THEN 
                    jsonb_build_object(
                        'old', row_to_json(OLD),
                        'new', row_to_json(NEW)
                    )
                ELSE row_to_json(NEW)
            END
        );
        
        PERFORM send_webhook_notification(
            edge_function_url,
            'trip.' || lower(TG_OP),
            notification_payload
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- ===========================
-- DATA AGGREGATION JOBS
-- ===========================

-- Update trip statistics daily
SELECT cron.schedule(
    'update-trip-statistics',
    '0 6 * * *', -- Run at 6 AM daily
    $$
    -- Create or update materialized view for trip statistics
    REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS trip_statistics;
    $$
);

-- Generate memory embeddings for new content
SELECT cron.schedule(
    'generate-memory-embeddings',
    '*/30 * * * *', -- Run every 30 minutes
    $$
    -- This would typically call an Edge Function to generate embeddings
    -- For now, we'll mark memories that need embedding
    UPDATE memories 
    SET metadata = jsonb_set(
        COALESCE(metadata, '{}'),
        '{needs_embedding}',
        'true'
    )
    WHERE embedding IS NULL
    AND created_at > NOW() - INTERVAL '1 hour';
    $$
);

-- ===========================
-- HEALTH CHECK JOBS
-- ===========================

-- Monitor database health and connections
SELECT cron.schedule(
    'monitor-database-health',
    '*/5 * * * *', -- Run every 5 minutes
    $$
    INSERT INTO system_metrics (metric_type, metric_name, value, metadata)
    SELECT 
        'database',
        'active_connections',
        count(*),
        jsonb_build_object(
            'by_state', jsonb_object_agg(state, count),
            'by_application', jsonb_object_agg(application_name, count)
        )
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY ROLLUP(state), ROLLUP(application_name);
    $$
);

-- ===========================
-- JOB MANAGEMENT FUNCTIONS
-- ===========================

-- Function to list all scheduled jobs
CREATE OR REPLACE FUNCTION list_scheduled_jobs()
RETURNS TABLE (
    jobid BIGINT,
    schedule TEXT,
    command TEXT,
    nodename TEXT,
    nodeport INTEGER,
    database TEXT,
    username TEXT,
    active BOOLEAN
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        jobid,
        schedule,
        command,
        nodename,
        nodeport,
        database,
        username,
        active
    FROM cron.job
    ORDER BY jobid;
$$;

-- Function to get job execution history
CREATE OR REPLACE FUNCTION get_job_history(
    job_name TEXT DEFAULT NULL,
    limit_rows INTEGER DEFAULT 100
)
RETURNS TABLE (
    jobid BIGINT,
    job_name TEXT,
    status TEXT,
    return_message TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTERVAL
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        d.jobid,
        j.jobname,
        d.status,
        d.return_message,
        d.start_time,
        d.end_time,
        d.end_time - d.start_time AS duration
    FROM cron.job_run_details d
    JOIN cron.job j ON j.jobid = d.jobid
    WHERE (job_name IS NULL OR j.jobname = job_name)
    ORDER BY d.start_time DESC
    LIMIT limit_rows;
$$;

-- ===========================
-- MONITORING TABLES
-- ===========================

-- Create notifications table if it doesn't exist
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

-- Create system metrics table for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value NUMERIC NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, read) 
WHERE read = false;

CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time 
ON system_metrics(metric_type, created_at DESC);