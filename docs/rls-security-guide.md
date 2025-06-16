# RLS Security Guide: Fixing Critical Policy Vulnerabilities

## Overview

This guide addresses the 8 critical RLS (Row Level Security) policy failures identified in the TripSage database and provides comprehensive solutions to ensure proper user data isolation and collaboration permissions.

## Critical Security Issues Identified

### 1. **trips - SELECT (other_user)**: Users can access other users' trips
**Problem**: The RLS policy allows users to see trips they shouldn't have access to.
**Impact**: Data breach - users can view private trip information.

### 2. **memories - SELECT (other_user)**: Users can access other users' memories
**Problem**: Memory isolation is broken, allowing cross-user data access.
**Impact**: Privacy violation - users can see AI memory data from other users.

### 3. **trips - UPDATE (viewer)**: Viewers can update trips when they should be read-only
**Problem**: Collaboration permission hierarchy is not enforced.
**Impact**: Data integrity - view-only users can modify trip data.

### 4. **trips - SELECT (non_collaborator)**: Non-collaborators can access shared trips
**Problem**: Collaboration filtering is not working correctly.
**Impact**: Unauthorized access to shared trip data.

### 5. **flights - SELECT (non_collaborator)**: Non-collaborators can access flight data
**Problem**: Trip-related data doesn't properly inherit trip permissions.
**Impact**: Flight booking details exposed to unauthorized users.

### 6. **search_destinations - SELECT (other_user)**: Users can access other users' search cache
**Problem**: Search cache isolation is broken.
**Impact**: Search history and preferences leaked between users.

### 7. **notifications - SELECT (other_user)**: Users can access other users' notifications
**Problem**: Notification isolation is not working.
**Impact**: Privacy breach - users can see notifications meant for others.

### 8. **notifications - UPDATE (other_user)**: Users can update other users' notifications
**Problem**: Users can modify notification state for other users.
**Impact**: Data tampering - users can mark others' notifications as read.

## Root Causes Analysis

### 1. **Subquery Performance Issues**
Some policies used subqueries like `(SELECT auth.uid())` which can cause performance issues and potential bypass scenarios in certain edge cases.

### 2. **Incomplete Permission Checks**
Collaboration policies didn't properly distinguish between view, edit, and admin permissions.

### 3. **Missing User Isolation**
Some tables lacked proper `user_id = auth.uid()` checks for basic user isolation.

### 4. **Cascade Permission Failures**
Trip-related tables (flights, accommodations) didn't properly inherit trip permissions.

## Comprehensive Solution

### Fixed RLS Policies

#### 1. **Trips Table - Proper User Isolation & Collaboration**

```sql
-- SELECT: Users can view owned trips or shared trips
CREATE POLICY "trips_select_policy" ON trips
FOR SELECT
TO authenticated
USING (
    -- User owns the trip
    user_id = auth.uid()
    OR
    -- User is a collaborator on the trip
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
    )
);

-- UPDATE: Only owners and edit/admin collaborators can update
CREATE POLICY "trips_update_policy" ON trips
FOR UPDATE
TO authenticated
USING (
    -- User owns the trip
    user_id = auth.uid()
    OR
    -- User has edit or admin permissions (NOT view-only)
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    -- Same conditions for WITH CHECK
    user_id = auth.uid()
    OR
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
        AND tc.permission_level IN ('edit', 'admin')
    )
);
```

#### 2. **Memories Table - Strict User Isolation**

```sql
-- All operations: Users can only access their own memories
CREATE POLICY "memories_user_isolation" ON memories
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());
```

#### 3. **Flights Table - Collaboration Inheritance**

```sql
-- SELECT: Inherit trip permissions
CREATE POLICY "flights_select_policy" ON flights
FOR SELECT
TO authenticated
USING (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User is a collaborator on the trip
        SELECT tc.trip_id FROM trip_collaborators tc WHERE tc.user_id = auth.uid()
    )
);

-- MODIFY: Only owners and edit/admin collaborators
CREATE POLICY "flights_modify_policy" ON flights
FOR ALL
TO authenticated
USING (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
)
WITH CHECK (
    trip_id IN (
        -- User owns the trip
        SELECT id FROM trips WHERE user_id = auth.uid()
        UNION
        -- User has edit or admin permissions
        SELECT tc.trip_id FROM trip_collaborators tc 
        WHERE tc.user_id = auth.uid() 
        AND tc.permission_level IN ('edit', 'admin')
    )
);
```

#### 4. **Search Cache Tables - Complete User Isolation**

```sql
-- All search cache tables get strict user isolation
CREATE POLICY "search_destinations_user_isolation" ON search_destinations
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

CREATE POLICY "search_activities_user_isolation" ON search_activities
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

CREATE POLICY "search_flights_user_isolation" ON search_flights
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

CREATE POLICY "search_hotels_user_isolation" ON search_hotels
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());
```

#### 5. **Notifications Table - Fixed User Isolation**

```sql
-- Separate policies for each operation to avoid subquery issues
CREATE POLICY "notifications_user_isolation_select" ON notifications
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "notifications_user_isolation_update" ON notifications
FOR UPDATE
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

CREATE POLICY "notifications_user_isolation_insert" ON notifications
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- Service role can create notifications for any user
CREATE POLICY "notifications_service_role_insert" ON notifications
FOR INSERT
TO service_role
WITH CHECK (true);
```

## Collaboration Permission Hierarchy

### Permission Levels

1. **view**: Can read trip and related data only
2. **edit**: Can read and modify trip and related data  
3. **admin**: Can read, modify, and manage collaborators

### Implementation Pattern

```sql
-- For SELECT operations: All collaborators can view
WHERE user_id = auth.uid() 
   OR trip_id IN (SELECT trip_id FROM trip_collaborators WHERE user_id = auth.uid())

-- For MODIFY operations: Only edit/admin collaborators
WHERE user_id = auth.uid() 
   OR trip_id IN (
       SELECT trip_id FROM trip_collaborators 
       WHERE user_id = auth.uid() 
       AND permission_level IN ('edit', 'admin')
   )
```

## Performance Optimizations

### Critical Indexes

```sql
-- Collaboration lookup optimization
CREATE INDEX idx_trip_collaborators_user_trip 
ON trip_collaborators(user_id, trip_id);

-- Permission filtering optimization
CREATE INDEX idx_trip_collaborators_trip_permission 
ON trip_collaborators(trip_id, permission_level) 
WHERE permission_level IN ('edit', 'admin');

-- User isolation optimization
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
```

## Common RLS Mistakes to Avoid

### 1. **Using Subqueries in USING Clauses**
```sql
-- ❌ WRONG - Can cause performance issues
USING (user_id = (SELECT auth.uid()))

-- ✅ CORRECT - Direct function call
USING (user_id = auth.uid())
```

### 2. **Not Using FORCE ROW LEVEL SECURITY**
```sql
-- ✅ Always force RLS on critical tables
ALTER TABLE trips FORCE ROW LEVEL SECURITY;
```

### 3. **Forgetting WITH CHECK Clauses**
```sql
-- ❌ INCOMPLETE - Only checks reads
FOR UPDATE USING (user_id = auth.uid())

-- ✅ COMPLETE - Checks reads and writes
FOR UPDATE 
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid())
```

### 4. **Not Testing with Real Users**
- Always test RLS policies with actual user sessions
- Use the provided real RLS test suite
- Test edge cases like permission changes mid-session

### 5. **Overly Complex Policies**
```sql
-- ❌ COMPLEX - Hard to debug and slow
USING (
    user_id = auth.uid() OR 
    id IN (
        SELECT t.id FROM trips t 
        JOIN trip_collaborators tc ON t.id = tc.trip_id 
        WHERE tc.user_id = auth.uid()
    )
)

-- ✅ SIMPLE - Clear and fast
USING (
    user_id = auth.uid()
    OR
    EXISTS (
        SELECT 1 FROM trip_collaborators tc 
        WHERE tc.trip_id = trips.id 
        AND tc.user_id = auth.uid()
    )
)
```

## Testing Strategy

### 1. **Automated Tests**
- Run the provided RLS test suite regularly
- Test both positive and negative cases
- Include performance benchmarks

### 2. **Manual Verification**
```sql
-- Test user isolation manually
SET ROLE authenticated;
SET request.jwt.claims TO '{"sub": "user1-uuid", "role": "authenticated"}';
SELECT * FROM trips; -- Should only show user1's trips

SET request.jwt.claims TO '{"sub": "user2-uuid", "role": "authenticated"}';
SELECT * FROM trips; -- Should only show user2's trips
```

### 3. **Security Audits**
- Review policies quarterly
- Test with penetration testing tools
- Monitor for policy bypass attempts

## Deployment Checklist

- [ ] Apply the comprehensive RLS fix migration
- [ ] Run full RLS test suite
- [ ] Verify all 8 security issues are resolved
- [ ] Test collaboration scenarios manually
- [ ] Monitor query performance post-deployment
- [ ] Document any custom policy requirements
- [ ] Set up automated RLS monitoring

## Monitoring & Maintenance

### 1. **Performance Monitoring**
```sql
-- Monitor slow RLS queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE query LIKE '%trip_collaborators%'
ORDER BY mean_exec_time DESC;
```

### 2. **Security Monitoring**
```sql
-- Check for policy violations in logs
SELECT * FROM auth.audit_log_entries 
WHERE error_message LIKE '%insufficient privilege%'
ORDER BY created_at DESC;
```

### 3. **Regular Audits**
- Monthly RLS policy review
- Quarterly security testing
- Annual penetration testing

## Conclusion

The comprehensive RLS policy fixes address all 8 critical security vulnerabilities by:

1. **Implementing strict user isolation** for personal data (memories, notifications, search cache)
2. **Enforcing proper collaboration permissions** with view/edit/admin hierarchy
3. **Ensuring trip-related data inheritance** for consistent access control
4. **Optimizing policy performance** with strategic indexes
5. **Following security best practices** to prevent common RLS mistakes

After applying these fixes, the TripSage database will have enterprise-grade security with proper multi-tenant isolation and collaboration features.