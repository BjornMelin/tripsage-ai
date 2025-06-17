# Supabase Extensions and Automation Configuration

This document provides comprehensive guidance for configuring and managing Supabase extensions and automation features in TripSage.

## Overview

TripSage utilizes several Supabase extensions to enable advanced functionality including:

- **pg_cron**: Automated scheduled jobs for maintenance and data processing
- **pg_net**: HTTP requests from database for webhook notifications
- **Realtime**: Live updates for collaborative features
- **Additional extensions**: Performance monitoring and security enhancements

## Extension Configuration

### Core Extensions

#### 1. pg_cron (Scheduled Jobs)

Enables automated database maintenance and scheduled tasks.

**Configuration:**

```sql
CREATE EXTENSION IF NOT EXISTS "pg_cron";
GRANT USAGE ON SCHEMA cron TO postgres;
ALTER SYSTEM SET cron.database_name = 'postgres';
```

**Scheduled Jobs:**

- **Daily Cache Cleanup** (2:00 AM): Removes expired search cache entries
- **Memory Cleanup** (3:00 AM): Archives old session memories
- **Trip Archival** (4:00 AM Sunday): Archives completed trips older than 1 year
- **Performance Stats** (1:00 AM): Updates table statistics for optimization
- **API Key Monitoring** (9:00 AM): Alerts for expiring API keys

#### 2. pg_net (HTTP Requests)

Enables webhook notifications and external API calls from the database.

**Configuration:**

```sql
CREATE EXTENSION IF NOT EXISTS "pg_net";
ALTER SYSTEM SET pg_net.batch_size = 200;
ALTER SYSTEM SET pg_net.ttl = '1 hour';
```

**Use Cases:**

- Trip collaboration notifications
- Booking status webhooks
- External service integrations
- Edge Function triggers

#### 3. Supabase Realtime

Provides live database updates for collaborative features.

**Tables with Realtime:**

- `trips` - Trip updates and collaboration
- `chat_messages` - Live chat functionality
- `chat_sessions` - Session status updates
- `trip_collaborators` - Collaboration changes
- `itinerary_items` - Itinerary modifications
- `chat_tool_calls` - AI tool execution status

### Performance Extensions

#### pg_stat_statements

Monitors query performance for optimization.

```sql
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
```

#### btree_gist

Provides advanced indexing for complex queries.

```sql
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### Security Extensions

#### pgcrypto

Handles encryption for sensitive data like API keys.

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

## Automated Maintenance Jobs

### Daily Jobs

#### Cache Cleanup (2:00 AM)

```sql
SELECT cron.schedule(
    'cleanup-expired-search-cache',
    '0 2 * * *',
    $$
    DELETE FROM search_destinations WHERE expires_at < NOW();
    DELETE FROM search_activities WHERE expires_at < NOW();
    DELETE FROM search_flights WHERE expires_at < NOW();
    DELETE FROM search_hotels WHERE expires_at < NOW();
    $$
);
```

#### Memory Management (3:00 AM)

```sql
SELECT cron.schedule(
    'cleanup-old-session-memories',
    '0 3 * * *',
    $$
    DELETE FROM session_memories 
    WHERE created_at < NOW() - INTERVAL '30 days';
    $$
);
```

#### Performance Optimization (1:00 AM)

```sql
SELECT cron.schedule(
    'update-table-statistics',
    '0 1 * * *',
    $$
    ANALYZE trips, flights, accommodations, chat_messages, memories;
    $$
);
```

### Weekly Jobs

#### Trip Archival (Sunday 4:00 AM)

```sql
SELECT cron.schedule(
    'archive-old-completed-trips',
    '0 4 * * 0',
    $$
    UPDATE trips 
    SET status = 'archived'
    WHERE status = 'completed' 
    AND updated_at < NOW() - INTERVAL '1 year';
    $$
);
```

#### Database Maintenance (Sunday 5:00 AM)

```sql
SELECT cron.schedule(
    'vacuum-tables',
    '0 5 * * 0',
    $$
    VACUUM ANALYZE trips, flights, accommodations, chat_messages, memories;
    $$
);
```

### High-Frequency Jobs

#### Memory Embedding Generation (Every 30 minutes)

```sql
SELECT cron.schedule(
    'generate-memory-embeddings',
    '*/30 * * * *',
    $$
    UPDATE memories 
    SET metadata = jsonb_set(COALESCE(metadata, '{}'), '{needs_embedding}', 'true')
    WHERE embedding IS NULL AND created_at > NOW() - INTERVAL '1 hour';
    $$
);
```

#### Health Monitoring (Every 5 minutes)

```sql
SELECT cron.schedule(
    'monitor-database-health',
    '*/5 * * * *',
    $$
    INSERT INTO system_metrics (metric_type, metric_name, value, metadata)
    SELECT 'database', 'active_connections', count(*), 
           jsonb_build_object('timestamp', NOW())
    FROM pg_stat_activity WHERE datname = current_database();
    $$
);
```

## Webhook Integration

### Configuration Tables

#### webhook_configs

Stores webhook endpoint configurations:

```sql
CREATE TABLE webhook_configs (
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
```

#### webhook_logs

Tracks webhook execution history:

```sql
CREATE TABLE webhook_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    webhook_config_id BIGINT REFERENCES webhook_configs(id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    attempt_count INTEGER DEFAULT 1,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### Event Types

#### Trip Events

- `trip.collaborator.added`
- `trip.collaborator.updated`
- `trip.collaborator.removed`

#### Chat Events

- `chat.message.created`
- `chat.session.started`
- `chat.session.ended`

#### Booking Events

- `booking.flights.booked`
- `booking.accommodations.booked`
- `booking.*.cancelled`

#### Processing Events

- `chat.message.process`
- `memory.generate.embedding`

### Webhook Functions

#### Core Webhook Sender

```sql
CREATE OR REPLACE FUNCTION send_webhook_with_retry(
    p_webhook_name TEXT,
    p_event_type TEXT,
    p_payload JSONB,
    p_attempt INTEGER DEFAULT 1
)
RETURNS BIGINT
```

#### Event-Specific Triggers

- `webhook_trip_collaboration()` - Handles collaboration events
- `webhook_chat_message()` - Processes chat messages
- `webhook_booking_status()` - Manages booking updates

## Edge Functions

### trip-events

Handles trip collaboration notifications and external integrations.

**Endpoint:** `/functions/v1/trip-events`
**Events:** Trip collaboration changes
**Actions:**

- Send user notifications
- Email alerts for collaborators
- External calendar sync triggers

### ai-processing

Manages AI-related tasks like embedding generation and preference extraction.

**Endpoint:** `/functions/v1/ai-processing`
**Events:** Chat message processing, memory embedding
**Actions:**

- Generate embeddings for new content
- Extract user preferences from messages
- Update long-term memory patterns

## Monitoring and Management

### Job Management Functions

#### List Scheduled Jobs

```sql
SELECT * FROM list_scheduled_jobs();
```

#### Get Job History

```sql
SELECT * FROM get_job_history('cleanup-expired-search-cache', 50);
```

#### Test Webhook

```sql
SELECT test_webhook('trip_events', '{"test": true, "timestamp": "now"}'::JSONB);
```

### Health Verification

#### Extension Status

```sql
SELECT * FROM verify_extensions();
```

#### Automation Setup

```sql
SELECT * FROM verify_automation_setup();
```

#### Webhook Statistics

```sql
SELECT * FROM get_webhook_stats('trip_events', 7);
```

### Monitoring Tables

#### notifications

User notifications from automated processes:

- API key expiration alerts
- Trip collaboration invites
- Booking confirmations

#### system_metrics

Database performance and health metrics:

- Connection counts
- Query performance
- Resource utilization

## Configuration Best Practices

### 1. Environment Setup

```bash
# Required environment variables
SUPABASE_URL=your-project-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-key (for embeddings)
EMAIL_SERVICE_URL=your-email-service-url (optional)
```

### 2. Security Considerations

- Use service role key only in Edge Functions
- Implement webhook signature verification
- Encrypt sensitive configuration data
- Monitor webhook logs for security events

### 3. Performance Optimization

- Schedule maintenance jobs during low-traffic periods
- Implement retry logic with exponential backoff
- Monitor job execution times and adjust schedules
- Use connection pooling for external API calls

### 4. Error Handling

- Implement comprehensive logging for all automated tasks
- Set up alerts for failed jobs or webhooks
- Maintain rollback procedures for critical operations
- Regular review of error logs and performance metrics

## Migration and Deployment

### Applying Extensions

1. Run the migration file: `20250611_02_enable_automation_extensions.sql`
2. Verify extension installation with `verify_automation_setup()`
3. Configure webhook endpoints in the `webhook_configs` table
4. Deploy Edge Functions to handle webhook events
5. Test automation with `test_webhook()` function

### Production Considerations

- Enable pg_stat_statements for query monitoring
- Configure appropriate log retention policies
- Set up external monitoring for job failures
- Implement backup procedures for configuration tables
- Document all custom job schedules and webhook configurations

## Troubleshooting

### Common Issues

#### pg_cron not working

- Verify extension is installed: `SELECT * FROM pg_extension WHERE extname = 'pg_cron';`
- Check database configuration: `SHOW cron.database_name;`
- Review job logs: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC;`

#### Webhooks failing

- Check webhook configuration: `SELECT * FROM webhook_configs WHERE is_active = true;`
- Review webhook logs: `SELECT * FROM webhook_logs WHERE response_status >= 400;`
- Test connectivity: `SELECT test_webhook('webhook_name');`

#### Realtime not updating

- Verify publication exists: `SELECT * FROM pg_publication WHERE pubname = 'supabase_realtime';`
- Check table inclusion: `SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';`
- Confirm client subscription settings in frontend

### Debugging Tools

- `verify_automation_setup()` - Overall system health
- `list_scheduled_jobs()` - View all cron jobs
- `get_webhook_stats()` - Webhook performance metrics
- `SELECT * FROM system_metrics ORDER BY created_at DESC LIMIT 100;` - Recent metrics

This comprehensive automation setup ensures TripSage operates efficiently with minimal manual intervention while providing robust monitoring and notification capabilities.
