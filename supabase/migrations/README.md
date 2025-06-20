# TripSage Database Migrations

This directory contains all database migration files for the TripSage Supabase project, following Supabase best practices for schema versioning and deployment.

## 📋 Overview

Database migrations are SQL scripts that track and apply changes to your database schema over time. They ensure consistency between development, staging, and production environments.

## 📁 Migration Files

| Migration | Purpose | Status |
|-----------|---------|--------|
| `20250609_02_consolidated_production_schema.sql` | Initial production schema with all core tables | ✅ Applied |
| `20250611_02_add_api_key_usage_tables.sql` | API key usage tracking and analytics | ✅ Applied |
| `20250611_02_add_business_logic_triggers.sql` | Automated triggers for data consistency | ✅ Applied |
| `20250611_02_enable_automation_extensions.sql` | Enable required PostgreSQL extensions | ✅ Applied |
| `20250614_01_extended_rls_policies.sql` | Enhanced Row Level Security policies | ✅ Applied |
| `20250616_03_configuration_rls_policies.sql` | Configuration table security policies | ✅ Applied |
| `20250111_01_add_storage_infrastructure.sql` | Storage buckets and file management | ✅ Applied |

## 🚀 Working with Migrations

### Creating a New Migration

1. **Generate from declarative schemas:**

   ```bash
   # Stop local database first
   supabase db stop
   
   # Generate migration from schema changes
   supabase db diff --file descriptive_migration_name
   ```

2. **Create manual migration:**

   ```bash
   supabase migration new descriptive_migration_name
   ```

3. **Migration naming convention:**
   - Format: `YYYYMMDD_NN_descriptive_name.sql`
   - Example: `20250617_01_add_user_preferences.sql`

### Applying Migrations

**Local Development:**

```bash
# Reset database and apply all migrations
supabase db reset

# Or apply specific migration
psql $DATABASE_URL -f supabase/migrations/20250617_01_add_user_preferences.sql
```

**Production Deployment:**

```bash
# Link to production project
supabase link --project-ref your-project-ref

# Push all pending migrations
supabase db push

# Verify migration status
supabase migration list
```

## 📝 Migration Best Practices

### 1. **Always Test Locally First**

```bash
# Test migration on local database
supabase db reset
# Verify application still works
```

### 2. **Write Idempotent Migrations**

```sql
-- Good: Check if exists
CREATE TABLE IF NOT EXISTS users (...);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences jsonb;

-- Bad: Will fail if already exists
CREATE TABLE users (...);
ALTER TABLE users ADD COLUMN preferences jsonb;
```

### 3. **Include Rollback Comments**

```sql
-- Migration: Add user preferences column
ALTER TABLE users ADD COLUMN preferences jsonb DEFAULT '{}';

-- Rollback: 
-- ALTER TABLE users DROP COLUMN preferences;
```

### 4. **Maintain Data Integrity**

```sql
-- Add constraint with validation
ALTER TABLE trips 
ADD CONSTRAINT check_dates 
CHECK (end_date >= start_date) 
NOT VALID;

-- Validate separately to avoid locking
ALTER TABLE trips VALIDATE CONSTRAINT check_dates;
```

### 5. **Handle Large Tables Carefully**

```sql
-- Use CONCURRENTLY for indexes on large tables
CREATE INDEX CONCURRENTLY idx_trips_user_id ON trips(user_id);

-- Add columns with defaults in steps
ALTER TABLE large_table ADD COLUMN new_col integer;
UPDATE large_table SET new_col = 0 WHERE new_col IS NULL;
ALTER TABLE large_table ALTER COLUMN new_col SET NOT NULL;
ALTER TABLE large_table ALTER COLUMN new_col SET DEFAULT 0;
```

## 🔍 Migration Patterns

### Adding a New Table

```sql
-- Create table with proper structure
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    theme text DEFAULT 'light',
    notifications jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT unique_user_preferences UNIQUE(user_id)
);

-- Add RLS policies
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own preferences"
ON public.user_preferences
FOR ALL TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Add indexes
CREATE INDEX idx_user_preferences_user_id ON public.user_preferences(user_id);

-- Add to search path if needed
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.user_preferences TO authenticated;
```

### Modifying Existing Tables

```sql
-- Add column with default
ALTER TABLE public.trips 
ADD COLUMN IF NOT EXISTS tags text[] DEFAULT '{}';

-- Add constraint
ALTER TABLE public.trips
ADD CONSTRAINT check_budget CHECK (budget >= 0);

-- Modify column type (be careful!)
ALTER TABLE public.trips
ALTER COLUMN notes TYPE text[] USING string_to_array(notes, ',');
```

### Adding Indexes

```sql
-- Simple index
CREATE INDEX IF NOT EXISTS idx_trips_created_at 
ON public.trips(created_at DESC);

-- Composite index
CREATE INDEX IF NOT EXISTS idx_trips_user_date 
ON public.trips(user_id, start_date);

-- Partial index
CREATE INDEX IF NOT EXISTS idx_active_trips 
ON public.trips(user_id) 
WHERE status = 'active';

-- GIN index for JSONB
CREATE INDEX IF NOT EXISTS idx_trips_metadata 
ON public.trips USING gin(search_metadata);
```

## 🔒 Security Migrations

### RLS Policy Updates

```sql
-- Drop old policy
DROP POLICY IF EXISTS "old_policy_name" ON public.trips;

-- Create new policy
CREATE POLICY "trips_select_policy"
ON public.trips FOR SELECT TO authenticated
USING (
    user_id = auth.uid() OR
    EXISTS (
        SELECT 1 FROM public.trip_collaborators
        WHERE trip_id = trips.id 
        AND user_id = auth.uid()
    )
);
```

### Function Security

```sql
-- Secure function with search_path
CREATE OR REPLACE FUNCTION public.get_user_trips(p_user_id uuid)
RETURNS SETOF trips
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT * FROM trips WHERE user_id = p_user_id;
$$;
```

## 🧪 Testing Migrations

### Pre-deployment Checklist

- [ ] Migration runs without errors locally
- [ ] Application tests pass
- [ ] RLS policies tested
- [ ] Performance impact assessed
- [ ] Rollback strategy documented

### Verification Queries

```sql
-- Verify table structure
\d+ table_name

-- Check RLS policies
SELECT * FROM pg_policies WHERE tablename = 'table_name';

-- Verify indexes
SELECT * FROM pg_indexes WHERE tablename = 'table_name';

-- Check constraints
SELECT * FROM information_schema.table_constraints 
WHERE table_name = 'table_name';
```

## 🚨 Troubleshooting

### Common Issues

1. **Migration already applied:**

   ```sql
   -- Check migration history
   SELECT * FROM supabase_migrations.schema_migrations 
   ORDER BY version DESC;
   ```

2. **Permission errors:**

   ```sql
   -- Grant necessary permissions
   GRANT ALL ON SCHEMA public TO postgres, anon, authenticated, service_role;
   ```

3. **Lock timeout:**

   ```sql
   -- Set lock timeout for migration
   SET lock_timeout = '10s';
   ```

4. **Foreign key violations:**

   ```sql
   -- Disable constraints temporarily
   SET session_replication_role = replica;
   -- Run migration
   SET session_replication_role = DEFAULT;
   ```

## 📊 Migration History

To view migration history in production:

```sql
SELECT 
    version,
    name,
    executed_at,
    execution_time
FROM supabase_migrations.schema_migrations
ORDER BY executed_at DESC;
```

## 🔗 Related Documentation

- [Declarative Schemas Guide](../schemas/README.md)
- [Local Development Guide](../README.md#quick-start)
- [Supabase Migration Docs](https://supabase.com/docs/guides/local-development/migrations)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don't_Do_This)

---

**Note:** Always backup your production database before applying migrations. Use `supabase db dump` for creating backups.
