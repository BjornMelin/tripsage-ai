-- Storage Infrastructure Migration
-- Description: Adds complete file storage infrastructure with buckets and RLS policies
-- Created: 2025-01-11
-- Version: 1.0

-- This migration sets up the complete storage infrastructure for TripSage,
-- including buckets for attachments, avatars, and trip images with
-- comprehensive RLS policies for secure file access.

-- ===========================
-- STORAGE SCHEMA SETUP
-- ===========================

-- Inlined storage bucket configuration (previously: \i ../storage/buckets.sql)

-- Create attachments bucket for trip files and chat attachments
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'attachments',
    'attachments', 
    false,
    52428800,
    ARRAY[
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/svg+xml'
    ],
    false
) ON CONFLICT (id) DO UPDATE
SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types,
    avif_autodetection = EXCLUDED.avif_autodetection;

-- Create avatars bucket for user profile images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'avatars',
    'avatars',
    true,
    5242880,
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/gif',
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

-- Create trip-images bucket for trip-related photos
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'trip-images',
    'trip-images',
    false,
    20971520,
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/avif',
        'image/heic',
        'image/heif'
    ],
    true
) ON CONFLICT (id) DO UPDATE
SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types,
    avif_autodetection = EXCLUDED.avif_autodetection;

-- ===========================
-- ADDITIONAL STORAGE TABLES
-- ===========================

-- Create file_processing_queue table for async file operations
CREATE TABLE IF NOT EXISTS file_processing_queue (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_attachment_id UUID NOT NULL,
    operation TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT file_processing_operation_check CHECK (operation IN ('virus_scan', 'thumbnail_generation', 'ocr', 'compression')),
    CONSTRAINT file_processing_priority_check CHECK (priority BETWEEN 1 AND 10),
    CONSTRAINT file_processing_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'))
);

-- Create file_versions table for version control
CREATE TABLE IF NOT EXISTS file_versions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_attachment_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    checksum TEXT NOT NULL,
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT false,
    change_description TEXT,
    
    CONSTRAINT file_versions_unique UNIQUE (file_attachment_id, version_number),
    CONSTRAINT file_versions_size_check CHECK (file_size > 0),
    CONSTRAINT file_versions_number_check CHECK (version_number > 0)
);

-- ===========================
-- STORAGE FUNCTIONS
-- ===========================

-- Generic trigger to set updated_at on row updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up orphaned files
CREATE OR REPLACE FUNCTION cleanup_orphaned_files()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Delete file_attachments records where upload failed after 24 hours
    DELETE FROM file_attachments
    WHERE upload_status = 'failed'
    AND created_at < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete processing queue entries older than 7 days
    DELETE FROM file_processing_queue
    WHERE status IN ('completed', 'failed', 'cancelled')
    AND completed_at < NOW() - INTERVAL '7 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get storage usage by user
CREATE OR REPLACE FUNCTION get_user_storage_usage(user_id UUID)
RETURNS TABLE(
    bucket_name TEXT,
    file_count BIGINT,
    total_size_bytes BIGINT,
    total_size_mb NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fa.bucket_name,
        COUNT(*)::BIGINT as file_count,
        SUM(fa.file_size)::BIGINT as total_size_bytes,
        ROUND(SUM(fa.file_size) / 1024.0 / 1024.0, 2) as total_size_mb
    FROM file_attachments fa
    WHERE fa.user_id = $1
    AND fa.upload_status = 'completed'
    GROUP BY fa.bucket_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check storage quota
CREATE OR REPLACE FUNCTION check_storage_quota(
    p_user_id UUID,
    p_file_size BIGINT,
    p_bucket_name TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    current_usage BIGINT;
    quota_limit BIGINT;
BEGIN
    -- Get current usage
    SELECT COALESCE(SUM(file_size), 0) INTO current_usage
    FROM file_attachments
    WHERE user_id = p_user_id
    AND bucket_name = p_bucket_name
    AND upload_status = 'completed';
    
    -- Set quota limits by bucket (in bytes)
    CASE p_bucket_name
        WHEN 'attachments' THEN quota_limit := 5368709120;  -- 5GB
        WHEN 'avatars' THEN quota_limit := 52428800;        -- 50MB
        WHEN 'trip-images' THEN quota_limit := 2147483648;  -- 2GB
        ELSE quota_limit := 1073741824;                     -- 1GB default
    END CASE;
    
    -- Check if new file would exceed quota
    RETURN (current_usage + p_file_size) <= quota_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================
-- STORAGE TRIGGERS
-- ===========================

-- Trigger to update file_attachments updated_at (create only if table exists)
DO $trg$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'file_attachments'
    ) THEN
        EXECUTE 'CREATE TRIGGER IF NOT EXISTS update_file_attachments_updated_at '
             || 'BEFORE UPDATE ON file_attachments '
             || 'FOR EACH ROW '
             || 'EXECUTE FUNCTION update_updated_at_column()';
    END IF;
END
$trg$;

-- Trigger to update file_processing_queue updated_at
CREATE TRIGGER update_file_processing_queue_updated_at
    BEFORE UPDATE ON file_processing_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================
-- STORAGE INDEXES
-- ===========================

-- Indexes for file_attachments (create only if table exists)
DO $idx$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'file_attachments'
    ) THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_file_attachments_user_id ON file_attachments(user_id)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_file_attachments_trip_id ON file_attachments(trip_id) WHERE trip_id IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_file_attachments_chat_message_id ON file_attachments(chat_message_id) WHERE chat_message_id IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_file_attachments_upload_status ON file_attachments(upload_status)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_file_attachments_virus_scan ON file_attachments(virus_scan_status) WHERE virus_scan_status != ''clean''';
    END IF;
END
$idx$;

-- Indexes for file_processing_queue
CREATE INDEX idx_file_processing_queue_status ON file_processing_queue(status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_file_processing_queue_scheduled ON file_processing_queue(scheduled_at) WHERE status = 'pending';

-- Indexes for file_versions
CREATE INDEX idx_file_versions_attachment_id ON file_versions(file_attachment_id);
CREATE INDEX idx_file_versions_current ON file_versions(file_attachment_id) WHERE is_current = true;

-- ===========================
-- STORAGE RLS POLICIES
-- ===========================

-- Enable RLS on new tables
ALTER TABLE file_processing_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_versions ENABLE ROW LEVEL SECURITY;

-- File processing queue policies (service role only)
CREATE POLICY "Service role manages file processing queue"
    ON file_processing_queue
    TO service_role
    USING (true)
    WITH CHECK (true);

-- File versions policies
-- Only create the SELECT policy when file_attachments exists to avoid hard dependency
DO $$
BEGIN
    IF to_regclass('public.file_attachments') IS NOT NULL THEN
        EXECUTE $pol$
            CREATE POLICY "Users can view versions of their files"
            ON file_versions FOR SELECT
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM file_attachments fa
                    WHERE fa.id = file_versions.file_attachment_id
                    AND fa.user_id = auth.uid()
                )
            )
        $pol$;
    END IF;
END $$;

CREATE POLICY "Service role manages file versions"
    ON file_versions
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ===========================
-- MIGRATION COMPLETION LOG
-- ===========================

DO $$
BEGIN
    RAISE NOTICE 'Storage Infrastructure Migration completed successfully!';
    RAISE NOTICE 'Created:';
    RAISE NOTICE '- ✅ Storage buckets (attachments, avatars, trip-images)';
    RAISE NOTICE '- ✅ Storage RLS policies with trip collaboration support';
    RAISE NOTICE '- ✅ File processing queue table';
    RAISE NOTICE '- ✅ File versions table';
    RAISE NOTICE '- ✅ Storage utility functions';
    RAISE NOTICE '- ✅ Performance indexes';
    RAISE NOTICE '';
    RAISE NOTICE 'Storage Features:';
    RAISE NOTICE '- 📁 Multi-bucket architecture with different quotas';
    RAISE NOTICE '- 🔒 Comprehensive RLS policies respecting trip permissions';
    RAISE NOTICE '- 🔄 File versioning support';
    RAISE NOTICE '- 🛡️ Virus scanning integration points';
    RAISE NOTICE '- 📊 Storage quota management';
    RAISE NOTICE '- 🧹 Automated cleanup functions';
END $$;

-- ===========================
-- VERIFICATION QUERIES
-- ===========================

-- Verify storage tables
SELECT 
    tablename,
    hasindexes,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('file_attachments', 'file_processing_queue', 'file_versions')
ORDER BY tablename;

-- Verify storage functions
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('cleanup_orphaned_files', 'get_user_storage_usage', 'check_storage_quota')
ORDER BY routine_name;

-- ===========================
-- POST-DEPLOYMENT NOTES
-- ===========================

-- IMPORTANT: After running this migration, you should:
-- 1. Configure Edge Functions for file processing webhooks
-- 2. Set up virus scanning service integration
-- 3. Configure CDN for public buckets
-- 4. Test file upload/download flows
-- 5. Monitor storage usage and adjust quotas
-- 6. Set up scheduled job for cleanup_orphaned_files()

-- ===========================
-- INLINED STORAGE POLICIES (previously policies.sql)
-- ===========================

CREATE OR REPLACE FUNCTION public.user_has_trip_access(user_id UUID, trip_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.trips t WHERE t.id = trip_id AND t.user_id = user_id
        UNION
        SELECT 1 FROM public.trip_collaborators tc WHERE tc.trip_id = trip_id AND tc.user_id = user_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.extract_trip_id_from_path(file_path TEXT)
RETURNS BIGINT AS $$
DECLARE trip_id_text TEXT;
BEGIN
    trip_id_text := substring(file_path from 'trip[s]?[_/](\d+)');
    IF trip_id_text IS NULL THEN RETURN NULL; END IF;
    RETURN trip_id_text::BIGINT;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE POLICY "Users can upload attachments to their trips"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'attachments' AND (
    public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
    OR name LIKE 'user_' || auth.uid()::TEXT || '/%'
  )
);

-- Base view policy for attachments without depending on public.file_attachments
CREATE POLICY "Users can view attachments from accessible trips"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'attachments' AND (
    public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
    OR name LIKE 'user_' || auth.uid()::TEXT || '/%'
  )
);

-- Optional additional view policy leveraging file_attachments ownership when available
DO $$
BEGIN
    IF to_regclass('public.file_attachments') IS NOT NULL THEN
        EXECUTE $pol$
            CREATE POLICY "Users can view attachments they own by record"
            ON storage.objects FOR SELECT TO authenticated
            USING (
              bucket_id = 'attachments' AND EXISTS (
                  SELECT 1 FROM public.file_attachments fa
                  WHERE fa.file_path = name AND fa.user_id = auth.uid()
              )
            )
        $pol$;
    END IF;
END $$;

CREATE POLICY "Users can update their own attachments"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'attachments' AND owner = auth.uid())
WITH CHECK (bucket_id = 'attachments' AND owner = auth.uid());

CREATE POLICY "Users can delete their own attachments"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'attachments' AND (
    owner = auth.uid() OR public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
  )
);

CREATE POLICY "Anyone can view avatars" ON storage.objects FOR SELECT TO public USING (bucket_id = 'avatars');

CREATE POLICY "Users can upload their own avatar"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'avatars' AND (
    name = auth.uid()::TEXT || '.jpg' OR name = auth.uid()::TEXT || '.png' OR name = auth.uid()::TEXT || '.gif' OR name = auth.uid()::TEXT || '.webp' OR name = auth.uid()::TEXT || '.avif'
  )
);

CREATE POLICY "Users can update their own avatar"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'avatars' AND owner = auth.uid())
WITH CHECK (bucket_id = 'avatars' AND owner = auth.uid());

CREATE POLICY "Users can delete their own avatar"
ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'avatars' AND owner = auth.uid());

CREATE POLICY "Users can upload trip images" ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'trip-images' AND public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name)));

-- Base policy: members can view trip images
CREATE POLICY "Users can view trip images" ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'trip-images' AND public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
);

-- Optional policy: allow viewing images from public trips when trips table exists
DO $$
BEGIN
    IF to_regclass('public.trips') IS NOT NULL THEN
        EXECUTE $pol$
            CREATE POLICY "Users can view public trip images"
            ON storage.objects FOR SELECT TO authenticated
            USING (
              bucket_id = 'trip-images' AND EXISTS (
                  SELECT 1 FROM public.trips t
                  WHERE t.id = public.extract_trip_id_from_path(name)
                  AND t.is_public = true
              )
            )
        $pol$;
    END IF;
END $$;

CREATE POLICY "Users can update their trip images" ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'trip-images' AND owner = auth.uid())
WITH CHECK (bucket_id = 'trip-images' AND owner = auth.uid());

CREATE POLICY "Users can delete trip images" ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'trip-images' AND (
    owner = auth.uid() OR public.user_has_trip_access(auth.uid(), public.extract_trip_id_from_path(name))
  )
);

CREATE POLICY "Service role has full access" ON storage.objects TO service_role USING (true) WITH CHECK (true);
