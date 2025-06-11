-- Storage Configuration for TripSage
-- Description: Additional storage configuration and utility functions
-- Created: 2025-01-11
-- Version: 1.0

-- ===========================
-- STORAGE CONFIGURATION
-- ===========================

-- Create thumbnails bucket for generated thumbnails
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'thumbnails',
    'thumbnails',
    false,  -- Private (controlled by RLS)
    10485760,  -- 10MB file size limit
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/avif'
    ],
    true
) ON CONFLICT (id) DO UPDATE
SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types,
    avif_autodetection = EXCLUDED.avif_autodetection;

-- Create quarantine bucket for infected files
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'quarantine',
    'quarantine',
    false,  -- Private (admin only)
    104857600,  -- 100MB file size limit
    ARRAY[]::TEXT[],  -- Allow any file type for quarantine
    false
) ON CONFLICT (id) DO UPDATE
SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types,
    avif_autodetection = EXCLUDED.avif_autodetection;

-- ===========================
-- STORAGE CORS CONFIGURATION
-- ===========================

-- Note: CORS configuration should be set via Supabase Dashboard or CLI
-- Example CORS settings for browser uploads:
-- {
--   "allowedOrigins": ["http://localhost:3000", "https://your-domain.com"],
--   "allowedMethods": ["GET", "POST", "PUT", "DELETE"],
--   "allowedHeaders": ["authorization", "x-client-info", "apikey", "content-type"],
--   "maxAgeSeconds": 3600
-- }

-- ===========================
-- STORAGE WEBHOOK FUNCTIONS
-- ===========================

-- Function to notify file processor Edge Function
CREATE OR REPLACE FUNCTION notify_file_processor()
RETURNS TRIGGER AS $$
DECLARE
    webhook_url TEXT;
BEGIN
    -- Get webhook URL from environment or configuration
    webhook_url := current_setting('app.file_processor_webhook_url', true);
    
    IF webhook_url IS NULL OR webhook_url = '' THEN
        -- Fallback URL - replace with your actual Edge Function URL
        webhook_url := 'https://your-project.supabase.co/functions/v1/file-processor';
    END IF;
    
    -- Only process completed uploads
    IF NEW.upload_status = 'completed' AND (OLD.upload_status IS NULL OR OLD.upload_status != 'completed') THEN
        PERFORM net.http_post(
            url := webhook_url,
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || current_setting('app.service_role_key', true)
            ),
            body := json_build_object(
                'type', TG_OP,
                'table', TG_TABLE_NAME,
                'record', row_to_json(NEW),
                'old_record', row_to_json(OLD)
            )::text
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================
-- STORAGE UTILITY FUNCTIONS
-- ===========================

-- Function to get file URL with signed URL for private buckets
CREATE OR REPLACE FUNCTION get_file_url(
    p_bucket_name TEXT,
    p_file_path TEXT,
    p_expires_in INTEGER DEFAULT 3600
) RETURNS TEXT AS $$
DECLARE
    is_public BOOLEAN;
    base_url TEXT;
BEGIN
    -- Check if bucket is public
    SELECT public INTO is_public
    FROM storage.buckets
    WHERE id = p_bucket_name;
    
    -- Get base URL
    base_url := current_setting('app.supabase_url', true) || '/storage/v1/object/';
    
    IF is_public THEN
        -- Return public URL
        RETURN base_url || 'public/' || p_bucket_name || '/' || p_file_path;
    ELSE
        -- Return signed URL endpoint (client must call this with proper auth)
        RETURN base_url || 'sign/' || p_bucket_name || '/' || p_file_path || '?expiresIn=' || p_expires_in;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate file upload
CREATE OR REPLACE FUNCTION validate_file_upload(
    p_user_id UUID,
    p_bucket_name TEXT,
    p_file_size BIGINT,
    p_mime_type TEXT,
    p_trip_id BIGINT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    validation_result JSONB := '{"valid": true, "errors": []}'::JSONB;
    bucket_info RECORD;
    user_quota_exceeded BOOLEAN;
    trip_access BOOLEAN := true;
BEGIN
    -- Get bucket information
    SELECT * INTO bucket_info
    FROM storage.buckets
    WHERE id = p_bucket_name;
    
    IF NOT FOUND THEN
        validation_result := jsonb_set(validation_result, '{valid}', 'false');
        validation_result := jsonb_set(validation_result, '{errors}', 
            (validation_result->'errors') || '["Invalid bucket name"]');
        RETURN validation_result;
    END IF;
    
    -- Check file size limit
    IF p_file_size > bucket_info.file_size_limit THEN
        validation_result := jsonb_set(validation_result, '{valid}', 'false');
        validation_result := jsonb_set(validation_result, '{errors}', 
            (validation_result->'errors') || 
            jsonb_build_array('File size exceeds limit of ' || 
                (bucket_info.file_size_limit / 1024 / 1024)::TEXT || 'MB'));
    END IF;
    
    -- Check MIME type
    IF bucket_info.allowed_mime_types IS NOT NULL AND 
       array_length(bucket_info.allowed_mime_types, 1) > 0 AND
       NOT (p_mime_type = ANY(bucket_info.allowed_mime_types)) THEN
        validation_result := jsonb_set(validation_result, '{valid}', 'false');
        validation_result := jsonb_set(validation_result, '{errors}', 
            (validation_result->'errors') || '["File type not allowed"]');
    END IF;
    
    -- Check user quota
    SELECT check_storage_quota(p_user_id, p_file_size, p_bucket_name) INTO user_quota_exceeded;
    IF NOT user_quota_exceeded THEN
        validation_result := jsonb_set(validation_result, '{valid}', 'false');
        validation_result := jsonb_set(validation_result, '{errors}', 
            (validation_result->'errors') || '["Storage quota exceeded"]');
    END IF;
    
    -- Check trip access if trip_id provided
    IF p_trip_id IS NOT NULL THEN
        SELECT storage.user_has_trip_access(p_user_id, p_trip_id) INTO trip_access;
        IF NOT trip_access THEN
            validation_result := jsonb_set(validation_result, '{valid}', 'false');
            validation_result := jsonb_set(validation_result, '{errors}', 
                (validation_result->'errors') || '["No access to specified trip"]');
        END IF;
    END IF;
    
    RETURN validation_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================
-- STORAGE TRIGGERS
-- ===========================

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS file_attachments_processor_trigger ON file_attachments;

-- Create trigger to notify file processor
CREATE TRIGGER file_attachments_processor_trigger
    AFTER INSERT OR UPDATE ON file_attachments
    FOR EACH ROW
    EXECUTE FUNCTION notify_file_processor();

-- ===========================
-- STORAGE RLS POLICIES FOR NEW BUCKETS
-- ===========================

-- Thumbnails bucket policies
CREATE POLICY "Users can view thumbnails of their files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'thumbnails' AND
    EXISTS (
        SELECT 1 FROM file_attachments fa
        WHERE fa.file_path = replace(name, 'thumbnails/', '')
        AND fa.user_id = auth.uid()
    )
);

-- Quarantine bucket policies (admin only)
CREATE POLICY "Only service role can access quarantine"
ON storage.objects
TO service_role
USING (bucket_id = 'quarantine')
WITH CHECK (bucket_id = 'quarantine');

-- ===========================
-- CONFIGURATION VIEWS
-- ===========================

-- View for storage configuration summary
CREATE OR REPLACE VIEW storage_configuration AS
SELECT 
    b.id as bucket_id,
    b.name as bucket_name,
    b.public,
    b.file_size_limit / 1024 / 1024 as size_limit_mb,
    array_length(b.allowed_mime_types, 1) as allowed_types_count,
    b.avif_autodetection,
    COUNT(o.id) as total_files,
    COALESCE(SUM(o.metadata->>'size')::BIGINT, 0) / 1024 / 1024 as used_space_mb
FROM storage.buckets b
LEFT JOIN storage.objects o ON b.id = o.bucket_id
GROUP BY b.id, b.name, b.public, b.file_size_limit, b.allowed_mime_types, b.avif_autodetection;

-- ===========================
-- VERIFICATION QUERIES
-- ===========================

-- Check all storage buckets
SELECT * FROM storage_configuration ORDER BY bucket_id;

-- Check storage policies
SELECT 
    policyname,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
AND policyname LIKE '%thumbnail%' OR policyname LIKE '%quarantine%'
ORDER BY policyname;

-- ===========================
-- POST-DEPLOYMENT NOTES
-- ===========================

-- IMPORTANT: After applying this configuration:
-- 1. Update app.file_processor_webhook_url setting with your Edge Function URL
-- 2. Update app.service_role_key setting for webhook authentication
-- 3. Configure CORS settings via Supabase Dashboard
-- 4. Test file upload validation functions
-- 5. Monitor webhook trigger functionality