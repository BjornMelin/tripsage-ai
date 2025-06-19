-- Storage Buckets Configuration for TripSage
-- Description: Defines storage buckets for file attachments, avatars, and trip images
-- Created: 2025-01-11
-- Version: 1.0

-- ===========================
-- STORAGE BUCKET CREATION
-- ===========================

-- Create attachments bucket for trip files and chat attachments
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types, avif_autodetection)
VALUES (
    'attachments',
    'attachments', 
    false,  -- Private bucket (requires authentication)
    52428800,  -- 50MB file size limit
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
    true,  -- Public bucket (profile images are publicly viewable)
    5242880,  -- 5MB file size limit
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/avif'
    ],
    true  -- Enable AVIF auto-detection for better compression
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
    false,  -- Private by default (controlled by RLS policies)
    20971520,  -- 20MB file size limit
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/avif',
        'image/heic',
        'image/heif'
    ],
    true  -- Enable AVIF auto-detection
) ON CONFLICT (id) DO UPDATE
SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types,
    avif_autodetection = EXCLUDED.avif_autodetection;

-- ===========================
-- BUCKET METADATA
-- ===========================

COMMENT ON COLUMN storage.buckets.id IS 'Unique identifier for the storage bucket';
COMMENT ON COLUMN storage.buckets.name IS 'Human-readable name for the bucket';
COMMENT ON COLUMN storage.buckets.public IS 'Whether files in this bucket are publicly accessible';
COMMENT ON COLUMN storage.buckets.file_size_limit IS 'Maximum file size in bytes';
COMMENT ON COLUMN storage.buckets.allowed_mime_types IS 'Array of allowed MIME types for uploads';

-- ===========================
-- VERIFICATION QUERY
-- ===========================

SELECT 
    id,
    name,
    public,
    file_size_limit / 1024 / 1024 as size_limit_mb,
    array_length(allowed_mime_types, 1) as allowed_types_count,
    avif_autodetection
FROM storage.buckets
WHERE id IN ('attachments', 'avatars', 'trip-images')
ORDER BY id;

-- ===========================
-- POST-DEPLOYMENT NOTES
-- ===========================

-- IMPORTANT: After creating buckets, you should:
-- 1. Apply RLS policies from policies.sql
-- 2. Configure CORS settings if needed for browser uploads
-- 3. Set up webhook for virus scanning integration
-- 4. Configure CDN for public buckets (avatars)
-- 5. Monitor storage usage and adjust limits as needed