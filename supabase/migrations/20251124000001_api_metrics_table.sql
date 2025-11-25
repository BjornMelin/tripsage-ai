-- API Metrics table for dashboard metrics collection
-- Created: 2025-11-24
-- Part of nuclear refactor for 2025-compliant dashboard metrics system

-- ===========================
-- API METRICS TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS public.api_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms NUMERIC NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_type TEXT,
    rate_limit_key TEXT,
    CONSTRAINT api_metrics_status_code_check CHECK (status_code >= 100 AND status_code < 600),
    CONSTRAINT api_metrics_duration_ms_check CHECK (duration_ms >= 0),
    CONSTRAINT api_metrics_method_check CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'))
);

-- ===========================
-- INDEXES FOR QUERY PERFORMANCE
-- ===========================
-- Primary query pattern: time-based aggregation
CREATE INDEX idx_api_metrics_created_at ON public.api_metrics(created_at DESC);

-- Secondary: endpoint-specific queries
CREATE INDEX idx_api_metrics_endpoint ON public.api_metrics(endpoint);

-- User-specific queries (partial index for space efficiency)
CREATE INDEX idx_api_metrics_user_id ON public.api_metrics(user_id) WHERE user_id IS NOT NULL;

-- Status code filtering for error rate calculation
CREATE INDEX idx_api_metrics_status_code ON public.api_metrics(status_code);

-- Composite index for common dashboard query pattern
CREATE INDEX idx_api_metrics_time_status ON public.api_metrics(created_at DESC, status_code);

-- ===========================
-- ROW LEVEL SECURITY
-- ===========================
ALTER TABLE public.api_metrics ENABLE ROW LEVEL SECURITY;

-- Admin read policy: Only authenticated admins can view metrics
-- Uses profiles.is_admin column for admin check
CREATE POLICY "admin_read_api_metrics" ON public.api_metrics
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_admin = true
        )
    );

-- Service role bypass: Allow service role full access for metrics recording
CREATE POLICY "service_role_all_api_metrics" ON public.api_metrics
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ===========================
-- DATA RETENTION (90-day policy)
-- ===========================
-- Schedule cleanup job via pg_cron (if available)
-- Deletes metrics older than 90 days, runs daily at 3 AM UTC
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'cleanup_api_metrics_90d',
            '0 3 * * *',
            $$DELETE FROM public.api_metrics WHERE created_at < NOW() - INTERVAL '90 days'$$
        );
    END IF;
END;
$$;

-- ===========================
-- COMMENTS
-- ===========================
COMMENT ON TABLE public.api_metrics IS 'API request metrics for dashboard analytics and observability';
COMMENT ON COLUMN public.api_metrics.endpoint IS 'API route pathname (e.g., /api/dashboard)';
COMMENT ON COLUMN public.api_metrics.method IS 'HTTP method (GET, POST, PUT, PATCH, DELETE)';
COMMENT ON COLUMN public.api_metrics.status_code IS 'HTTP response status code';
COMMENT ON COLUMN public.api_metrics.duration_ms IS 'Request duration in milliseconds';
COMMENT ON COLUMN public.api_metrics.user_id IS 'Authenticated user ID (null for anonymous requests)';
COMMENT ON COLUMN public.api_metrics.error_type IS 'Error class name for failed requests';
COMMENT ON COLUMN public.api_metrics.rate_limit_key IS 'Rate limit key used for this request';
