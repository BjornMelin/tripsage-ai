# TripSage RLS Implementation Guide

## Overview

This guide documents the Row Level Security (RLS) implementation for TripSage, following PostgreSQL and Supabase best practices for optimal performance and maintainability.

## Core Principles

1. **Simple policies** - Each policy has a single, clear condition
2. **Performance-first** - All RLS columns are indexed
3. **Wrapped functions** - `auth.uid()` wrapped in SELECT for caching
4. **Role-specific** - Policies target specific roles (authenticated, service_role)

## Table Classification

### User-Owned Tables (Full RLS)
Tables where users own and control their data:
- `trips` - User's travel plans
- `memories` - User preferences and history
- `api_keys` - User's API credentials
- `chat_sessions` - User's chat history
- `notifications` - User's notifications
- `search_*` tables - User's search caches

### Collaborative Tables (Shared Access)
Tables supporting shared access patterns:
- `trip_collaborators` - Manages trip sharing permissions
- `flights`, `accommodations`, `itinerary_items` - Inherit trip permissions

### System Tables (Restricted Access)
Tables managed by the system:
- `system_metrics` - Performance metrics (service_role only)
- `webhook_configs` - Webhook settings (service_role only)
- `webhook_logs` - Webhook activity (service_role only)

## Policy Patterns

### 1. User Isolation Pattern
```sql
-- Basic user data isolation
CREATE POLICY "Users can view own data"
ON table_name
FOR SELECT
TO authenticated
USING (user_id = (SELECT auth.uid()));
```

### 2. Collaborative Access Pattern
```sql
-- Trip collaboration via join
CREATE POLICY "Collaborators can view trips"
ON trips
FOR SELECT
TO authenticated
USING (
    user_id = (SELECT auth.uid())
    OR 
    id IN (
        SELECT trip_id 
        FROM trip_collaborators 
        WHERE user_id = (SELECT auth.uid())
    )
);
```

### 3. Cascade Permission Pattern
```sql
-- Child tables inherit parent permissions
CREATE POLICY "Access via trip permissions"
ON flights
FOR ALL
TO authenticated
USING (
    trip_id IN (
        SELECT id FROM trips 
        WHERE user_id = (SELECT auth.uid())
        UNION
        SELECT trip_id FROM trip_collaborators 
        WHERE user_id = (SELECT auth.uid())
    )
);
```

### 4. System Table Pattern
```sql
-- Restrict to service role only
CREATE POLICY "Service role only"
ON system_metrics
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Block authenticated users
CREATE POLICY "No user access"
ON system_metrics
FOR ALL
TO authenticated
USING (false)
WITH CHECK (false);
```

## Performance Optimizations

### 1. Critical Indexes
```sql
-- User isolation indexes
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_memories_user_id ON memories(user_id);

-- Collaboration indexes
CREATE INDEX idx_collaborators_user_trip ON trip_collaborators(user_id, trip_id);
CREATE INDEX idx_collaborators_trip_user ON trip_collaborators(trip_id, user_id);

-- Status/filtering indexes
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, read) 
WHERE read = false;
```

### 2. Function Optimization
All RLS policies use wrapped functions for caching:
- `(SELECT auth.uid())` instead of `auth.uid()`
- Security definer functions for complex logic

### 3. Application-Level Filtering
Always add explicit filters in queries:
```javascript
// Good - explicit filter helps query planner
const trips = await supabase
  .from('trips')
  .select('*')
  .eq('user_id', userId);
```

## Testing Strategy

### 1. Unit Tests
Located in `tests/database/test_rls_policies.py`:
- User data isolation
- Collaboration permissions
- Anonymous access blocking
- System table restrictions
- Performance impact (<10ms target)

### 2. Test Execution
```bash
# Run RLS tests
uv run pytest tests/database/test_rls_policies.py -v

# Generate test report
uv run python tests/database/test_rls_policies.py
```

### 3. Manual Testing
```sql
-- Test as different users
SET LOCAL role TO authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "user-id-here"}';
SELECT * FROM trips; -- Should only see user's trips

-- Test as anonymous
SET LOCAL role TO anon;
SELECT * FROM trips; -- Should see nothing
```

## Security Considerations

1. **Always enable RLS** - Use `ALTER TABLE ENABLE ROW LEVEL SECURITY`
2. **Force RLS** - Use `FORCE ROW LEVEL SECURITY` for critical tables
3. **No DELETE policies** - Notifications/audit tables have no delete access
4. **Service role isolation** - System tables only accessible by service role

## Common Operations

### Adding a New User Table
```sql
-- 1. Create table with user_id
CREATE TABLE new_table (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- other columns
);

-- 2. Enable RLS
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
ALTER TABLE new_table FORCE ROW LEVEL SECURITY;

-- 3. Add basic policy
CREATE POLICY "Users can manage own data"
ON new_table
FOR ALL
TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

-- 4. Add index
CREATE INDEX idx_new_table_user_id ON new_table(user_id);
```

### Adding Collaboration
```sql
-- Add policy for shared access
CREATE POLICY "Shared access via parent"
ON child_table
FOR SELECT
TO authenticated
USING (
    parent_id IN (
        SELECT id FROM parent_table
        WHERE /* parent access logic */
    )
);
```

## Maintenance

1. **Monitor slow queries** - Check for missing indexes
2. **Review policy complexity** - Refactor complex policies into functions
3. **Test with realistic data** - Performance changes with scale
4. **Keep policies simple** - One condition per policy when possible

## Resources

- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Project RLS tests: `tests/database/test_rls_policies.py`
- Schema files: `supabase/schemas/05_policies*.sql`