-- Extended RLS Policies Migration
-- Description: Add Row Level Security policies for automation and webhook tables
-- Dependencies: 20250609_02_consolidated_production_schema.sql

BEGIN;

-- ===========================
-- NOTIFICATIONS TABLE POLICIES
-- ===========================

-- Enable RLS on notifications table
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;

-- Users can only view their own notifications
CREATE POLICY "Users can view their own notifications"
ON notifications
FOR SELECT
TO authenticated
USING (user_id = (SELECT auth.uid()));

-- Users can update their own notifications (mark as read)
CREATE POLICY "Users can update their own notifications"
ON notifications
FOR UPDATE
TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

-- System can create notifications for any user (via service role)
CREATE POLICY "System can create notifications"
ON notifications
FOR INSERT
TO service_role
WITH CHECK (true);

-- ===========================
-- SYSTEM METRICS TABLE POLICIES
-- ===========================

-- Enable RLS on system_metrics table
ALTER TABLE system_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics FORCE ROW LEVEL SECURITY;

-- Only service role can insert metrics (automated jobs)
CREATE POLICY "Service role can insert metrics"
ON system_metrics
FOR INSERT
TO service_role
WITH CHECK (true);

-- Authenticated users can view aggregated metrics only
CREATE POLICY "No direct access to system metrics"
ON system_metrics
FOR SELECT
TO authenticated
USING (false);  -- No direct access

-- Create secure view for metrics access
CREATE OR REPLACE VIEW public.system_metrics_summary
WITH (security_invoker = true) AS
SELECT 
    metric_type,
    metric_name,
    DATE_TRUNC('hour', created_at) as hour,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count
FROM system_metrics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY metric_type, metric_name, DATE_TRUNC('hour', created_at);

-- Grant access to the view
GRANT SELECT ON public.system_metrics_summary TO authenticated;

-- ===========================
-- WEBHOOK CONFIGS TABLE POLICIES
-- ===========================

-- Enable RLS on webhook_configs table
ALTER TABLE webhook_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_configs FORCE ROW LEVEL SECURITY;

-- Only service role can manage webhook configurations
CREATE POLICY "Service role manages webhook configs"
ON webhook_configs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- No access for regular authenticated users
CREATE POLICY "No user access to webhook configs"
ON webhook_configs
FOR ALL
TO authenticated
USING (false)
WITH CHECK (false);

-- ===========================
-- WEBHOOK LOGS TABLE POLICIES
-- ===========================

-- Enable RLS on webhook_logs table
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs FORCE ROW LEVEL SECURITY;

-- Service role can insert and view webhook logs
CREATE POLICY "Service role manages webhook logs"
ON webhook_logs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Authenticated users cannot access webhook logs directly
CREATE POLICY "No user access to webhook logs"
ON webhook_logs
FOR ALL
TO authenticated
USING (false)
WITH CHECK (false);

-- ===========================
-- HELPER FUNCTIONS FOR SECURE ACCESS
-- ===========================

-- Function to get notification count for current user
CREATE OR REPLACE FUNCTION get_unread_notification_count()
RETURNS INTEGER
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT COUNT(*)::INTEGER
    FROM notifications
    WHERE user_id = auth.uid()
    AND read = false;
$$;

-- Function to mark notifications as read
CREATE OR REPLACE FUNCTION mark_notifications_read(notification_ids BIGINT[])
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE notifications
    SET read = true
    WHERE id = ANY(notification_ids)
    AND user_id = auth.uid()
    AND read = false;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

-- Function to get user's recent notifications
CREATE OR REPLACE FUNCTION get_recent_notifications(
    limit_count INTEGER DEFAULT 10,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id BIGINT,
    type TEXT,
    title TEXT,
    message TEXT,
    read BOOLEAN,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT id, type, title, message, read, metadata, created_at
    FROM notifications
    WHERE user_id = auth.uid()
    ORDER BY created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
$$;

-- ===========================
-- PERFORMANCE INDEXES
-- ===========================

-- Notification indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread 
ON notifications(user_id, read) 
WHERE read = false;

CREATE INDEX IF NOT EXISTS idx_notifications_user_created 
ON notifications(user_id, created_at DESC);

-- System metrics indexes (already exist in 07_automation.sql)
-- CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time 
-- ON system_metrics(metric_type, created_at DESC);

-- Webhook logs indexes
CREATE INDEX IF NOT EXISTS idx_webhook_logs_config_created 
ON webhook_logs(webhook_config_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_event_type 
ON webhook_logs(event_type, created_at DESC);

-- ===========================
-- VERIFICATION
-- ===========================

DO $$
BEGIN
    RAISE NOTICE 'Extended RLS Policies Migration Applied Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'New policies added for:';
    RAISE NOTICE '- ✅ notifications table (user isolation)';
    RAISE NOTICE '- ✅ system_metrics table (service role only)';
    RAISE NOTICE '- ✅ webhook_configs table (service role only)';
    RAISE NOTICE '- ✅ webhook_logs table (service role only)';
    RAISE NOTICE '';
    RAISE NOTICE 'Helper functions added:';
    RAISE NOTICE '- ✅ get_unread_notification_count()';
    RAISE NOTICE '- ✅ mark_notifications_read()';
    RAISE NOTICE '- ✅ get_recent_notifications()';
    RAISE NOTICE '';
    RAISE NOTICE 'Security summary:';
    RAISE NOTICE '- Users can only access their own notifications';
    RAISE NOTICE '- System metrics are aggregated through secure view';
    RAISE NOTICE '- Webhook configuration is restricted to service role';
END $$;

-- Verify RLS is enabled on the new tables
SELECT 
    tablename,
    rowsecurity,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = t.tablename) as policy_count
FROM pg_tables t
WHERE schemaname = 'public' 
    AND tablename IN ('notifications', 'system_metrics', 'webhook_configs', 'webhook_logs')
ORDER BY tablename;

COMMIT;