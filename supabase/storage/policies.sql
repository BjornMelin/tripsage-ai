-- Storage RLS Policies for TripSage
-- Description: Implements Row Level Security policies for storage buckets
-- Created: 2025-01-11
-- Version: 1.0

-- ===========================
-- HELPER FUNCTIONS
-- ===========================

-- Function to check if user has access to a trip (owner or collaborator)
CREATE OR REPLACE FUNCTION storage.user_has_trip_access(user_id UUID, trip_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.trips t
        WHERE t.id = trip_id AND t.user_id = user_id
        
        UNION
        
        SELECT 1 FROM public.trip_collaborators tc
        WHERE tc.trip_id = trip_id AND tc.user_id = user_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to extract trip_id from file path
CREATE OR REPLACE FUNCTION storage.extract_trip_id_from_path(file_path TEXT)
RETURNS BIGINT AS $$
DECLARE
    trip_id_text TEXT;
BEGIN
    -- Extract trip ID from paths like: trip_123/file.pdf or trips/123/file.pdf
    trip_id_text := substring(file_path from 'trip[s]?[_/](\d+)');
    
    IF trip_id_text IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN trip_id_text::BIGINT;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===========================
-- ATTACHMENTS BUCKET POLICIES
-- ===========================

-- Policy: Users can upload files to trips they own or collaborate on
CREATE POLICY "Users can upload attachments to their trips"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'attachments' AND
    (
        -- User owns or collaborates on the trip
        storage.user_has_trip_access(auth.uid(), storage.extract_trip_id_from_path(name))
        OR
        -- User is uploading to their own user folder
        name LIKE 'user_' || auth.uid()::TEXT || '/%'
    )
);

-- Policy: Users can view attachments from trips they have access to
CREATE POLICY "Users can view attachments from accessible trips"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'attachments' AND
    (
        -- User owns or collaborates on the trip
        storage.user_has_trip_access(auth.uid(), storage.extract_trip_id_from_path(name))
        OR
        -- User is accessing their own files
        name LIKE 'user_' || auth.uid()::TEXT || '/%'
        OR
        -- File is explicitly shared (check file_attachments table)
        EXISTS (
            SELECT 1 FROM public.file_attachments fa
            WHERE fa.file_path = name
            AND fa.user_id = auth.uid()
        )
    )
);

-- Policy: Users can update their own attachments
CREATE POLICY "Users can update their own attachments"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'attachments' AND
    owner = auth.uid()
)
WITH CHECK (
    bucket_id = 'attachments' AND
    owner = auth.uid()
);

-- Policy: Users can delete their own attachments
CREATE POLICY "Users can delete their own attachments"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'attachments' AND
    (
        owner = auth.uid()
        OR
        -- Trip owners can delete any attachment in their trip
        EXISTS (
            SELECT 1 FROM public.trips t
            WHERE t.id = storage.extract_trip_id_from_path(name)
            AND t.user_id = auth.uid()
        )
    )
);

-- ===========================
-- AVATARS BUCKET POLICIES
-- ===========================

-- Policy: Anyone can view avatars (public bucket)
CREATE POLICY "Anyone can view avatars"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'avatars');

-- Policy: Users can upload their own avatar
CREATE POLICY "Users can upload their own avatar"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'avatars' AND
    name = auth.uid()::TEXT || '.jpg' OR
    name = auth.uid()::TEXT || '.png' OR
    name = auth.uid()::TEXT || '.gif' OR
    name = auth.uid()::TEXT || '.webp' OR
    name = auth.uid()::TEXT || '.avif'
);

-- Policy: Users can update their own avatar
CREATE POLICY "Users can update their own avatar"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'avatars' AND
    owner = auth.uid()
)
WITH CHECK (
    bucket_id = 'avatars' AND
    owner = auth.uid()
);

-- Policy: Users can delete their own avatar
CREATE POLICY "Users can delete their own avatar"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'avatars' AND
    owner = auth.uid()
);

-- ===========================
-- TRIP-IMAGES BUCKET POLICIES
-- ===========================

-- Policy: Users can upload images to trips they own or collaborate on
CREATE POLICY "Users can upload trip images"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'trip-images' AND
    storage.user_has_trip_access(auth.uid(), storage.extract_trip_id_from_path(name))
);

-- Policy: Users can view images from trips they have access to
CREATE POLICY "Users can view trip images"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'trip-images' AND
    (
        -- User has access to the trip
        storage.user_has_trip_access(auth.uid(), storage.extract_trip_id_from_path(name))
        OR
        -- Trip is marked as public (future feature)
        EXISTS (
            SELECT 1 FROM public.trips t
            WHERE t.id = storage.extract_trip_id_from_path(name)
            AND t.is_public = true  -- Assuming this column will be added
        )
    )
);

-- Policy: Users can update images they uploaded
CREATE POLICY "Users can update their trip images"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'trip-images' AND
    owner = auth.uid()
)
WITH CHECK (
    bucket_id = 'trip-images' AND
    owner = auth.uid()
);

-- Policy: Users can delete images they uploaded or if they own the trip
CREATE POLICY "Users can delete trip images"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'trip-images' AND
    (
        owner = auth.uid()
        OR
        EXISTS (
            SELECT 1 FROM public.trips t
            WHERE t.id = storage.extract_trip_id_from_path(name)
            AND t.user_id = auth.uid()
        )
    )
);

-- ===========================
-- SERVICE ROLE POLICIES
-- ===========================

-- Policy: Service role has full access to all buckets
CREATE POLICY "Service role has full access"
ON storage.objects
TO service_role
USING (true)
WITH CHECK (true);

-- ===========================
-- VERIFICATION QUERIES
-- ===========================

-- List all storage policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
ORDER BY policyname;

-- ===========================
-- POST-DEPLOYMENT NOTES
-- ===========================

-- IMPORTANT: After applying policies, you should:
-- 1. Test file upload/download for each bucket
-- 2. Verify trip collaboration permissions work correctly
-- 3. Test avatar upload and public access
-- 4. Implement client-side file validation
-- 5. Set up monitoring for policy violations