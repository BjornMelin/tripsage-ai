# Database Triggers Documentation

## Overview

This document details all database triggers implemented in the TripSage system for business logic automation, data integrity, and real-time event handling.

## Trigger Categories

### 1. Timestamp Management Triggers

Automatically update `updated_at` timestamps on record modifications.

**Tables with `updated_at` triggers:**
- trips
- flights
- accommodations
- chat_sessions
- api_keys
- memories
- file_attachments
- trip_collaborators
- itinerary_items
- transportation
- trip_notes
- saved_options
- trip_comparisons
- price_history

### 2. Collaboration Event Triggers

#### notify_trip_collaboration_changes
- **Event:** INSERT, UPDATE, DELETE on `trip_collaborators`
- **Function:** `notify_collaboration_change()`
- **Purpose:** Send real-time notifications via pg_notify when collaborators are added, updated, or removed
- **Notification Channel:** `trip_collaboration`
- **Payload:**
  ```json
  {
    "event_type": "collaborator_added|collaborator_updated|collaborator_removed",
    "trip_id": 123,
    "trip_name": "Summer Europe Trip",
    "user_id": "uuid",
    "user_email": "user@example.com",
    "added_by": "uuid",
    "added_by_email": "admin@example.com",
    "permission_level": "view|edit|admin",
    "timestamp": "2025-01-06T12:00:00Z",
    "operation": "INSERT|UPDATE|DELETE"
  }
  ```

#### validate_collaboration_permissions_trigger
- **Event:** BEFORE INSERT or UPDATE on `trip_collaborators`
- **Function:** `validate_collaboration_permissions()`
- **Purpose:** Enforce permission hierarchy rules
- **Rules:**
  - Only trip owners can grant admin permissions
  - Non-owners need admin permission to modify collaborators
  - Users cannot modify their own permission level
  - Admins cannot grant admin permissions to others

#### audit_trip_collaboration_changes
- **Event:** AFTER UPDATE on `trip_collaborators`
- **Function:** `audit_collaboration_changes()`
- **Purpose:** Create audit trail for collaboration changes
- **Audit Storage:** `session_memories` table with metadata type `collaboration_audit`

### 3. Cache Invalidation Triggers

#### notify_cache_invalidation
- **Tables:** trips, flights, accommodations
- **Event:** INSERT, UPDATE, DELETE
- **Notification Channel:** `cache_invalidation`
- **Payload:**
  ```json
  {
    "event_type": "cache_invalidation",
    "table_name": "trips",
    "record_id": "123",
    "operation": "UPDATE",
    "timestamp": "2025-01-06T12:00:00Z"
  }
  ```

#### cleanup_related_search_cache
- **Tables:** trips, accommodations, flights
- **Event:** INSERT, UPDATE
- **Purpose:** Automatically clean up related search cache entries
- **Behavior:**
  - Trips: Clear destination and activity searches
  - Accommodations: Clear hotel searches for location/date
  - Flights: Clear flight searches for route/date

### 4. Business Logic Triggers

#### auto_expire_inactive_sessions
- **Table:** chat_sessions
- **Event:** BEFORE UPDATE when updated_at changes
- **Function:** `auto_expire_chat_session()`
- **Purpose:** Automatically expire sessions inactive for 24+ hours
- **Notification Channel:** `chat_session_expired`

#### cleanup_message_attachments
- **Table:** chat_messages
- **Event:** AFTER DELETE
- **Function:** `cleanup_orphaned_attachments()`
- **Purpose:** Mark file attachments as orphaned when messages are deleted
- **Behavior:** Sets `metadata.orphaned = true` on related attachments

#### update_trip_status_from_bookings
- **Tables:** flights, accommodations
- **Event:** INSERT or UPDATE when booking_status changes
- **Function:** `update_trip_status_from_bookings()`
- **Purpose:** Automatically update trip status based on booking confirmations
- **Status Logic:**
  - All confirmed → trip status = 'confirmed'
  - Any cancelled → trip status = 'needs_attention'
  - Mixed/pending → trip status = 'in_progress'

## Scheduled Jobs (pg_cron)

### Daily Jobs

#### daily_cleanup_job
- **Schedule:** 2 AM UTC daily
- **Tasks:**
  - Expire inactive chat sessions (24h timeout)
  - Delete orphaned attachments older than 7 days
  - Clean up expired search cache
  - Remove old session memories (7+ days)
- **Logging:** Results stored in session_memories

### Weekly Jobs

#### weekly_maintenance_job
- **Schedule:** 3 AM UTC every Sunday
- **Tasks:**
  - Run database performance maintenance
  - Clean up orphaned collaborator records
  - Optimize vector indexes
- **Dependencies:** Calls `maintain_database_performance()`, `cleanup_orphaned_collaborators()`, `optimize_vector_indexes()`

### Monthly Jobs

#### monthly_cleanup_job
- **Schedule:** 4 AM UTC on the 1st of each month
- **Tasks:**
  - Deep clean old memories (keep last 365 days, max 1000 per user)
  - Generate collaboration statistics
  - Clean up audit logs older than 6 months
- **Reporting:** Stores collaboration statistics before cleanup

### Recurring Jobs

#### search_cache_cleanup
- **Schedule:** Every 6 hours
- **Function:** `cleanup_expired_search_cache()`
- **Purpose:** Remove expired search results from cache tables

#### expire_sessions
- **Schedule:** Every hour
- **Function:** `expire_inactive_sessions(24)`
- **Purpose:** Mark inactive sessions as expired

## Real-time Event Channels

### pg_notify Channels

1. **trip_collaboration**
   - Events: Collaborator added/updated/removed
   - Used by: WebSocket services for real-time updates

2. **cache_invalidation**
   - Events: Data changes requiring cache refresh
   - Used by: Cache service for invalidation

3. **chat_session_expired**
   - Events: Session auto-expiration
   - Used by: Chat services for cleanup

## Setup Instructions

### Enable pg_cron (Required for scheduled jobs)

```sql
-- Run as superuser
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant usage to database role
GRANT USAGE ON SCHEMA cron TO your_db_role;
```

### Schedule Jobs

```sql
-- Daily cleanup at 2 AM UTC
SELECT cron.schedule('daily-cleanup', '0 2 * * *', 'SELECT daily_cleanup_job();');

-- Weekly maintenance on Sundays at 3 AM UTC
SELECT cron.schedule('weekly-maintenance', '0 3 * * 0', 'SELECT weekly_maintenance_job();');

-- Monthly cleanup on the 1st at 4 AM UTC
SELECT cron.schedule('monthly-cleanup', '0 4 1 * *', 'SELECT monthly_cleanup_job();');

-- Search cache cleanup every 6 hours
SELECT cron.schedule('search-cache-cleanup', '0 */6 * * *', 'SELECT cleanup_expired_search_cache();');

-- Expire sessions every hour
SELECT cron.schedule('expire-sessions', '0 * * * *', 'SELECT expire_inactive_sessions(24);');
```

### Monitor Jobs

```sql
-- View scheduled jobs
SELECT * FROM cron.job;

-- View job run history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 50;

-- Check specific job status
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-cleanup')
ORDER BY start_time DESC 
LIMIT 10;
```

## Error Handling

All trigger functions include proper error handling:
- Permission violations raise exceptions with descriptive messages
- Audit failures are logged but don't block operations
- Notification failures don't affect core functionality
- Cleanup operations use safe DELETE with proper constraints

## Performance Considerations

1. **Trigger Overhead**
   - Notification triggers are lightweight (pg_notify is async)
   - Validation triggers only run on specific operations
   - Cache cleanup is condition-based to minimize unnecessary deletes

2. **Batch Operations**
   - Scheduled jobs process in batches to avoid long transactions
   - Cleanup functions return counts for monitoring
   - Vector index optimization is data-size aware

3. **Monitoring**
   - All maintenance jobs log to session_memories
   - Job results include performance metrics
   - Failed operations are tracked in pg_cron history

## Testing Triggers

```sql
-- Test collaboration notification
INSERT INTO trip_collaborators (trip_id, user_id, added_by, permission_level)
VALUES (1, 'user-uuid', 'owner-uuid', 'view');

-- Test cache invalidation
UPDATE trips SET destination = 'New York' WHERE id = 1;

-- Test session expiration
UPDATE chat_sessions 
SET updated_at = NOW() - INTERVAL '25 hours' 
WHERE id = 'session-uuid';

-- Manually run cleanup jobs
SELECT daily_cleanup_job();
SELECT weekly_maintenance_job();
SELECT monthly_cleanup_job();
```