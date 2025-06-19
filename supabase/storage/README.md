# TripSage Storage Infrastructure

This directory contains the complete file storage infrastructure configuration for TripSage.

## Files

### Core Configuration

- `buckets.sql` - Storage bucket definitions with size limits and MIME type restrictions
- `policies.sql` - Row Level Security policies for storage access control
- `config.sql` - Additional storage configuration, webhooks, and utility functions

### Edge Functions

- `../functions/file-processor/` - Edge Function for asynchronous file processing

### Deployment

- `../../scripts/database/deploy_storage_infrastructure.py` - Automated deployment script

## Quick Start

### 1. Deploy Storage Infrastructure

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
export DATABASE_URL="postgresql://postgres:password@host:port/postgres"

# Run deployment script
python scripts/database/deploy_storage_infrastructure.py
```

### 2. Deploy Edge Function

```bash
# Deploy file processor function
supabase functions deploy file-processor

# Set environment variables for the function
supabase secrets set SUPABASE_URL=your_supabase_url
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 3. Configure CORS (via Supabase Dashboard)

```json
{
  "allowedOrigins": ["http://localhost:3000", "https://your-domain.com"],
  "allowedMethods": ["GET", "POST", "PUT", "DELETE"],
  "allowedHeaders": ["authorization", "x-client-info", "apikey", "content-type"],
  "maxAgeSeconds": 3600
}
```

## Storage Buckets

| Bucket | Purpose | Size Limit | Access | File Types |
|--------|---------|------------|--------|------------|
| `attachments` | Trip documents, chat files | 50MB | Private | PDF, DOC, XLS, images, text |
| `avatars` | User profile images | 5MB | Public | Images only |
| `trip-images` | Trip photos and media | 20MB | Private | All image formats |
| `thumbnails` | Auto-generated thumbnails | 10MB | Private | Images only |
| `quarantine` | Infected/suspicious files | 100MB | Admin only | Any type |

## Security Features

### Access Control

- **Trip-based permissions**: Users can only access files from trips they own or collaborate on
- **User ownership**: Users can only modify files they uploaded
- **Collaboration respect**: File access follows trip collaboration permissions

### File Processing

- **Virus scanning**: All uploads are scanned for malware
- **Automatic quarantine**: Infected files are moved to secure quarantine bucket
- **Metadata extraction**: Document and image metadata is automatically extracted
- **Thumbnail generation**: Images get auto-generated thumbnails in multiple sizes

### Quotas

- **Per-user limits**: Prevent storage abuse with configurable quotas
- **Per-trip limits**: Manage storage costs at the trip level
- **Real-time checking**: Quota validation before upload acceptance

## API Usage

### Upload File

```typescript
// Validate upload first
const validation = await supabase.rpc('validate_file_upload', {
  p_user_id: userId,
  p_bucket_name: 'attachments',
  p_file_size: file.size,
  p_mime_type: file.type,
  p_trip_id: tripId
});

if (!validation.valid) {
  console.error('Upload validation failed:', validation.errors);
  return;
}

// Get signed upload URL
const { data, error } = await supabase.storage
  .from('attachments')
  .createSignedUploadUrl(`trip_${tripId}/documents/${filename}`);

// Upload file
const { error: uploadError } = await supabase.storage
  .from('attachments')
  .upload(data.path, file, { token: data.token });
```

### Download File

```typescript
// For private files, create signed URL
const { data, error } = await supabase.storage
  .from('attachments')
  .createSignedUrl(`trip_${tripId}/document.pdf`, 3600);

// For public files (avatars), get public URL
const { data } = supabase.storage
  .from('avatars')
  .getPublicUrl(`${userId}.jpg`);
```

### Check Storage Usage

```typescript
// Get user storage usage by bucket
const { data } = await supabase.rpc('get_user_storage_usage', {
  user_id: userId
});

console.log('Storage usage:', data);
```

## Monitoring

### Health Checks

```sql
-- Check bucket status
SELECT * FROM storage_configuration ORDER BY bucket_id;

-- Check processing queue
SELECT operation, status, COUNT(*) 
FROM file_processing_queue 
GROUP BY operation, status;

-- Check storage usage
SELECT bucket_name, SUM(file_size) / 1024 / 1024 as size_mb
FROM file_attachments 
WHERE upload_status = 'completed'
GROUP BY bucket_name;
```

### Cleanup

```sql
-- Clean up orphaned files (run daily)
SELECT cleanup_orphaned_files();

-- Clear old processing queue entries
DELETE FROM file_processing_queue
WHERE status = 'completed' AND completed_at < NOW() - INTERVAL '7 days';
```

## Troubleshooting

### Common Issues

1. **Upload failures**: Check file size, type, and user quotas
2. **Permission denied**: Verify trip collaboration permissions
3. **Processing delays**: Check Edge Function logs and processing queue
4. **Virus scan failures**: Verify antivirus service configuration

### Debug Queries

```sql
-- Check failed uploads
SELECT * FROM file_attachments 
WHERE upload_status = 'failed' 
ORDER BY created_at DESC;

-- Check virus scan results
SELECT virus_scan_status, COUNT(*) 
FROM file_attachments 
GROUP BY virus_scan_status;

-- Check RLS policy issues
SELECT * FROM pg_stat_activity 
WHERE query LIKE '%storage.objects%';
```

## Next Steps

1. **Test file upload flows** in your application
2. **Configure virus scanning service** (ClamAV or commercial)
3. **Set up CDN** for public buckets (optional)
4. **Monitor storage costs** and adjust quotas as needed
5. **Implement client-side upload progress** and error handling
