# Database Scripts

Database management scripts for schema initialization, migrations, and infrastructure deployment.

## Overview

These scripts manage the PostgreSQL database lifecycle including:

- Initial schema setup
- Migration management
- Storage infrastructure
- Triggers and functions
- Data integrity checks

## Migration System

### How Migrations Work

1. **Naming Convention**: `YYYYMMDD_description.sql`
   - Example: `20250615_add_user_preferences.sql`
   - Ensures chronological ordering

2. **Tracking**: Applied migrations are recorded in `migration_history` table
   - Prevents duplicate application
   - Tracks execution time and status

3. **Transaction Safety**: Each migration runs in a transaction
   - Automatic rollback on error
   - Maintains database consistency

### Running Migrations

```bash
# View pending migrations (dry run)
python scripts/database/run_migrations.py --dry-run

# Apply all pending migrations
python scripts/database/run_migrations.py

# Apply up to specific migration
python scripts/database/run_migrations.py --up-to 20250615_add_user_preferences.sql

# Use specific project
python scripts/database/run_migrations.py --project-id your-project-id
```

## Core Scripts

### init_database.py

Initialize a fresh database with base schema and required extensions.

**When to use**:

- Setting up new development environment
- Creating test databases
- Initial production deployment

**Features**:

- Creates all tables with proper constraints
- Sets up RLS policies
- Installs required extensions
- Seeds initial data (configurable)

**Usage**:

```bash
# Basic initialization
python scripts/database/init_database.py

# With seed data
python scripts/database/init_database.py --with-seed-data

# Specific environment
python scripts/database/init_database.py --env development
```

### run_migrations.py

Apply SQL migrations to update database schema.

**Features**:

- Automatic detection of pending migrations
- Dry-run mode for safety
- Detailed logging
- Rollback tracking

**Migration Guidelines**:

1. One logical change per migration
2. Include rollback commands in comments
3. Test in development first
4. Document breaking changes

### deploy_storage_infrastructure.py

Set up Supabase Storage buckets and policies.

**Manages**:

- Storage bucket creation
- Access policies
- CORS configuration
- File size limits

**Usage**:

```bash
# Deploy all storage infrastructure
python scripts/database/deploy_storage_infrastructure.py

# Deploy specific buckets
python scripts/database/deploy_storage_infrastructure.py --buckets avatars,documents

# Update policies only
python scripts/database/deploy_storage_infrastructure.py --policies-only
```

### deploy_triggers.py

Deploy database triggers and functions for automation.

**Includes**:

- Updated timestamp triggers
- Audit logging
- Data validation functions
- Event notifications

**Usage**:

```bash
# Deploy all triggers
python scripts/database/deploy_triggers.py

# Deploy specific trigger set
python scripts/database/deploy_triggers.py --type audit

# Remove triggers (cleanup)
python scripts/database/deploy_triggers.py --remove
```

## Migration Best Practices

### DO

- ✅ Test migrations on a copy of production data
- ✅ Include meaningful descriptions in filenames
- ✅ Write idempotent migrations when possible
- ✅ Add comments explaining complex changes
- ✅ Consider performance impact of migrations

### DON'T

- ❌ Modify data and schema in same migration
- ❌ Use `DROP COLUMN` without checking dependencies
- ❌ Assume column order in `INSERT` statements
- ❌ Forget to update application code for breaking changes
- ❌ Run untested migrations in production

## Writing Migrations

### Template

```sql
-- Migration: Brief description of changes
-- Author: Your Name
-- Date: YYYY-MM-DD

-- Add your migration SQL here
BEGIN;

-- Example: Add new column
ALTER TABLE users 
ADD COLUMN preferences JSONB DEFAULT '{}';

-- Example: Create index
CREATE INDEX idx_users_preferences ON users USING GIN (preferences);

-- Add comment for documentation
COMMENT ON COLUMN users.preferences IS 'User preferences including theme, language, etc.';

COMMIT;

-- Rollback commands (in comments for manual execution if needed)
-- ALTER TABLE users DROP COLUMN preferences;
```

### Common Patterns

**Adding Columns with Defaults**:

```sql
-- Safe way to add NOT NULL column
ALTER TABLE orders ADD COLUMN status TEXT;
UPDATE orders SET status = 'pending' WHERE status IS NULL;
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending';
```

**Renaming Safely**:

```sql
-- Rename column (check application code first!)
ALTER TABLE products RENAME COLUMN price TO unit_price;
```

**Creating Indexes Without Blocking**:

```sql
-- Create index concurrently (doesn't lock table)
CREATE INDEX CONCURRENTLY idx_orders_created_at ON orders(created_at);
```

## Troubleshooting

### Migration Failures

1. **Check error message**:

   ```bash
   python scripts/database/run_migrations.py 2>&1 | tee migration.log
   ```

2. **Verify migration status**:

   ```sql
   SELECT * FROM migration_history ORDER BY executed_at DESC LIMIT 10;
   ```

3. **Manual rollback if needed**:
   - Find rollback commands in migration file comments
   - Execute manually via SQL client
   - Update migration_history

### Connection Issues

1. **Verify environment variables**:

   ```bash
   echo $DATABASE_URL
   echo $SUPABASE_DB_URL
   ```

2. **Test connection**:

   ```bash
   python scripts/verification/verify_connection.py
   ```

3. **Check firewall/network**:
   - Ensure PostgreSQL port (5432) is accessible
   - Verify SSL requirements

## Performance Considerations

### Large Migrations

For migrations affecting many rows:

1. **Use batches**:

   ```sql
   -- Update in batches to avoid long locks
   DO $$
   DECLARE
     batch_size INT := 1000;
   BEGIN
     LOOP
       UPDATE users 
       SET new_field = calculate_value(old_field)
       WHERE new_field IS NULL
       LIMIT batch_size;
       
       EXIT WHEN NOT FOUND;
       PERFORM pg_sleep(0.1); -- Brief pause between batches
     END LOOP;
   END $$;
   ```

2. **Monitor progress**:

   ```sql
   -- In another session, monitor progress
   SELECT COUNT(*) FILTER (WHERE new_field IS NOT NULL) as done,
          COUNT(*) FILTER (WHERE new_field IS NULL) as remaining
   FROM users;
   ```

3. **Consider maintenance window** for very large changes

## Security

- All scripts use environment variables for credentials
- SQL injection prevention through parameterized queries
- Audit logging for compliance tracking
- Role-based access control (RLS) preservation

## Related Documentation

- [Database Schema Documentation](../../docs/database/schema.md)
- [Backup and Recovery Guide](../../docs/database/backup-recovery.md)
- [Performance Tuning Guide](../../docs/database/performance.md)
