# Supabase Edge Functions

This directory contains Edge Functions that handle various background processing tasks for the TripSage application.

## Available Functions

### 1. Trip Notifications (`trip-notifications`)
Handles trip collaboration notifications including user invitations, permission changes, and trip sharing.

**Features:**
- Email notifications via Resend API
- Webhook notifications to external services
- Real-time collaboration event processing
- Database trigger integration

**Endpoints:**
- `POST /functions/v1/trip-notifications` - Send manual notifications
- Webhook handler for database events

### 2. File Processing (`file-processing`)
Processes uploaded files including virus scanning, image optimization, and metadata extraction.

**Features:**
- Virus scanning integration (placeholder for production services)
- Image resizing and optimization
- File metadata extraction
- Automatic processing on file upload

**Endpoints:**
- `POST /functions/v1/file-processing` - Manual file processing
- Webhook handler for file upload events

### 3. Cache Invalidation (`cache-invalidation`)
Manages cache invalidation across Redis/DragonflyDB and database search caches.

**Features:**
- Redis/DragonflyDB cache clearing
- Search cache table cleanup
- Pattern-based cache invalidation
- Application layer notifications

**Endpoints:**
- `POST /functions/v1/cache-invalidation` - Manual cache invalidation
- Webhook handler for database change events

## Configuration

### Environment Variables

All functions require the following base environment variables:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# Webhook Security
WEBHOOK_SECRET=your_webhook_secret
```

### Function-Specific Environment Variables

#### Trip Notifications
```bash
# Email Service (optional)
RESEND_API_KEY=your_resend_api_key

# External Webhook (optional)
NOTIFICATION_WEBHOOK_URL=your_notification_webhook_url
```

#### File Processing
```bash
# Storage Configuration
STORAGE_BUCKET=attachments
MAX_FILE_SIZE=50000000

# Virus Scanning (optional)
VIRUS_SCAN_API_KEY=your_virus_scan_api_key
CLOUDFLARE_AI_TOKEN=your_cloudflare_token
```

#### Cache Invalidation
```bash
# Redis/DragonflyDB Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password

# Cache Webhook (optional)
CACHE_WEBHOOK_URL=your_cache_webhook_url
```

## Database Triggers

### Setting up Webhooks

To enable automatic processing, set up database webhooks for these tables:

1. **trip_collaborators** → trip-notifications
2. **file_attachments** → file-processing
3. **All tables** → cache-invalidation

Example webhook configuration:
```sql
-- Enable webhooks for trip_collaborators
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;

-- Function to send webhook
CREATE OR REPLACE FUNCTION send_webhook_notification()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('webhook_channel', json_build_object(
    'type', TG_OP,
    'table', TG_TABLE_NAME,
    'record', row_to_json(NEW),
    'old_record', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
    'schema', TG_TABLE_SCHEMA
  )::text);
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER trip_collaborators_webhook
  AFTER INSERT OR UPDATE OR DELETE ON trip_collaborators
  FOR EACH ROW EXECUTE FUNCTION send_webhook_notification();
```

## Deployment

### Using Supabase CLI

1. **Deploy all functions:**
```bash
supabase functions deploy
```

2. **Deploy specific function:**
```bash
supabase functions deploy trip-notifications
supabase functions deploy file-processing
supabase functions deploy cache-invalidation
```

3. **Set environment variables:**
```bash
supabase secrets set RESEND_API_KEY=your_key
supabase secrets set REDIS_URL=your_redis_url
# ... other secrets
```

### Testing Functions

1. **Test trip notifications:**
```bash
curl -X POST https://your-project.supabase.co/functions/v1/trip-notifications \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "collaboration_added",
    "trip_id": 123,
    "user_id": "user-uuid",
    "target_user_id": "target-uuid",
    "permission_level": "view"
  }'
```

2. **Test file processing:**
```bash
curl -X POST https://your-project.supabase.co/functions/v1/file-processing \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "file-uuid",
    "operation": "process_all"
  }'
```

3. **Test cache invalidation:**
```bash
curl -X POST https://your-project.supabase.co/functions/v1/cache-invalidation \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "cache_type": "all",
    "patterns": ["trip:*", "search:*"],
    "reason": "Manual cleanup"
  }'
```

## Monitoring and Logging

All functions include comprehensive logging and error handling:

- Request validation and authentication
- Detailed operation logging
- Error reporting and recovery
- Performance metrics (processing times)

Monitor function logs through the Supabase Dashboard or CLI:
```bash
supabase functions logs trip-notifications
```

## Security Considerations

1. **Authentication**: All functions validate JWT tokens
2. **Webhook Security**: Webhook endpoints verify secret tokens
3. **Input Validation**: All requests are validated for required fields
4. **Error Handling**: Sensitive information is not exposed in error responses
5. **Rate Limiting**: Consider implementing rate limiting for production use

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify SUPABASE_SERVICE_ROLE_KEY is set correctly
2. **Redis Connection**: Check REDIS_URL and password configuration
3. **Email Failures**: Verify RESEND_API_KEY and domain configuration
4. **File Processing**: Ensure proper Storage bucket permissions

### Debug Mode

Enable debug logging by setting environment variable:
```bash
SUPABASE_DEBUG=true
```

## Contributing

When adding new Edge Functions:

1. Follow the established directory structure
2. Use shared utilities from `_shared/` directory
3. Include comprehensive JSDoc documentation
4. Add appropriate error handling and logging
5. Update this README with new function details