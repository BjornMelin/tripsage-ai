# Script Usage Guide

A comprehensive guide for using TripSage automation scripts effectively and safely.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Environment Setup](#environment-setup)
3. [Common Workflows](#common-workflows)
4. [Script Categories](#script-categories)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Safety Guidelines](#safety-guidelines)

## Quick Reference

### Most Used Commands

```bash
# Verify setup
python scripts/testing/test_runner.py

# Initialize new environment
python scripts/database/init_database.py
python scripts/database/run_migrations.py

# Run tests
python scripts/testing/run_tests_with_coverage.py

# Check connections
python scripts/verification/verify_connection.py
python scripts/verification/verify_dragonfly.py

# Security audit
python scripts/security_validation.py
```

### Script Execution Order

For new environments:
1. Environment verification
2. Database initialization
3. Migration execution
4. Extension deployment
5. Service verification
6. Security validation

## Environment Setup

### Prerequisites

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd tripsage
   ```

2. **Python Environment**:
   ```bash
   # Create virtual environment
   python3.12 -m venv venv
   
   # Activate (Linux/Mac)
   source venv/bin/activate
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit with your values
   nano .env
   ```

Required variables:
```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SUPABASE_URL=https://project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Cache
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=optional-password

# Security
JWT_SECRET=your-secret-key
ENCRYPTION_KEY=your-encryption-key
```

### Service Dependencies

1. **PostgreSQL/Supabase**:
   - Version: 15+
   - Extensions: uuid-ossp, pgcrypto, pg_trgm
   - RLS enabled

2. **DragonflyDB/Redis**:
   - Version: 7+ (Redis) or latest (DragonflyDB)
   - Memory: 512MB minimum
   - Persistence: Optional but recommended

## Common Workflows

### Development Setup

```bash
# 1. Verify environment
python scripts/testing/test_runner.py

# 2. Setup database
python scripts/database/init_database.py --env development

# 3. Apply migrations
python scripts/database/run_migrations.py

# 4. Deploy extensions
python scripts/automation/deploy_extensions.py

# 5. Verify everything
python scripts/verification/verify_connection.py
python scripts/verification/verify_dragonfly.py
python scripts/verification/verify_extensions.py

# 6. Run tests
python scripts/testing/run_tests_with_coverage.py
```

### Daily Development

```bash
# Morning setup
./scripts/dev_setup.sh

# Before coding
python scripts/database/run_migrations.py --dry-run
python scripts/verification/verify_connection.py

# After changes
python scripts/testing/run_tests_with_coverage.py
python scripts/security_validation.py --quick

# Before commit
python scripts/testing/test_summary.py
```

### Production Deployment

```bash
# Pre-deployment
python scripts/security_validation.py --full
python scripts/verification/validate_schema_consistency.py

# Deployment
python scripts/database/run_migrations.py --dry-run
python scripts/database/run_migrations.py
python scripts/automation/deploy_extensions.py
python scripts/database/deploy_storage_infrastructure.py
python scripts/database/deploy_triggers.py

# Post-deployment
python scripts/verification/verify_extensions.py
python scripts/benchmarks/dragonfly_performance.py --quick
python scripts/security/rls_vulnerability_tests.sql
```

## Script Categories

### Database Scripts (`/database/`)

**Purpose**: Manage database schema, migrations, and infrastructure.

**Key Scripts**:
- `init_database.py`: Create fresh database
- `run_migrations.py`: Apply schema changes
- `deploy_storage_infrastructure.py`: Setup storage
- `deploy_triggers.py`: Install triggers

**Usage Pattern**:
```bash
# Always check before running
python script.py --dry-run

# Run with specific options
python script.py --env production --verbose

# Check results
python scripts/verification/validate_schema_consistency.py
```

### Verification Scripts (`/verification/`)

**Purpose**: Validate system health and connectivity.

**Key Scripts**:
- `verify_connection.py`: Database connectivity
- `verify_dragonfly.py`: Cache connectivity
- `verify_extensions.py`: Extension status
- `validate_schema_consistency.py`: Schema integrity

**Usage Pattern**:
```bash
# Quick health check
for script in scripts/verification/verify_*.py; do
    python "$script" || echo "Failed: $script"
done

# Detailed verification
python scripts/verification/verify_connection.py --verbose --test-operations
```

### Security Scripts (`/security/`)

**Purpose**: Security validation and vulnerability testing.

**Key Scripts**:
- `rls_vulnerability_tests.sql`: RLS policy testing
- `security_validation.py`: Comprehensive audit

**Usage Pattern**:
```bash
# Run SQL security tests
psql $DATABASE_URL -f scripts/security/rls_vulnerability_tests.sql

# Full security audit
python scripts/security_validation.py --compliance-report
```

### Testing Scripts (`/testing/`)

**Purpose**: Test execution and analysis.

**Key Scripts**:
- `run_tests_with_coverage.py`: Full test suite
- `test_summary.py`: Test result analysis
- `test_runner.py`: Quick smoke tests

**Usage Pattern**:
```bash
# Full test run
python scripts/testing/run_tests_with_coverage.py

# Quick check
python scripts/testing/test_runner.py

# Analyze results
python scripts/testing/test_summary.py
```

### Benchmark Scripts (`/benchmarks/`)

**Purpose**: Performance testing and optimization.

**Key Scripts**:
- `dragonfly_performance.py`: Cache benchmarks

**Usage Pattern**:
```bash
# Full benchmark
python scripts/benchmarks/dragonfly_performance.py

# Quick benchmark
python scripts/benchmarks/dragonfly_performance.py --quick

# Compare with baseline
python scripts/benchmarks/dragonfly_performance.py --compare baseline.json
```

## Best Practices

### 1. Always Use Dry Run

Most scripts support `--dry-run`:
```bash
# See what would happen
python scripts/database/run_migrations.py --dry-run

# If looks good, run for real
python scripts/database/run_migrations.py
```

### 2. Check Prerequisites

Before running scripts:
```bash
# Verify environment
python scripts/testing/test_runner.py

# Check connections
python scripts/verification/verify_connection.py
```

### 3. Use Proper Environment

```bash
# Development
export ENVIRONMENT=development
python scripts/database/init_database.py

# Production (be careful!)
export ENVIRONMENT=production
python scripts/database/run_migrations.py
```

### 4. Log Everything

```bash
# Capture output
python scripts/database/run_migrations.py 2>&1 | tee migration_$(date +%Y%m%d_%H%M%S).log

# Enable debug logging
export LOG_LEVEL=DEBUG
python scripts/verification/verify_connection.py
```

### 5. Version Control

```bash
# Before making changes
git status
git branch feature/my-changes

# After successful run
git add scripts/
git commit -m "chore: run migrations for feature X"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'tripsage'`

**Solution**:
```bash
# Ensure running from project root
cd /path/to/tripsage

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use the script from correct location
python scripts/database/run_migrations.py  # ✓ Good
cd scripts && python database/run_migrations.py  # ✗ Bad
```

#### 2. Connection Failures

**Problem**: `could not connect to database`

**Solution**:
```bash
# Check environment variables
echo $DATABASE_URL

# Test connection directly
psql $DATABASE_URL -c "SELECT 1"

# Check network
nc -zv database.host 5432

# Verify with script
python scripts/verification/verify_connection.py --verbose
```

#### 3. Permission Errors

**Problem**: `permission denied for schema public`

**Solution**:
```bash
# Check user permissions
psql $DATABASE_URL -c "\du"

# For Supabase, ensure using service key for admin operations
export SUPABASE_SERVICE_KEY=your-service-key
python scripts/database/deploy_extensions.py
```

#### 4. Migration Conflicts

**Problem**: `migration already applied`

**Solution**:
```sql
-- Check migration history
SELECT * FROM migration_history ORDER BY executed_at DESC;

-- If needed, manually mark as applied
INSERT INTO migration_history (filename, executed_at) 
VALUES ('20250615_migration_name.sql', NOW());
```

### Debug Mode

Enable detailed debugging:
```bash
# Python scripts
export LOG_LEVEL=DEBUG
export PYTHONPATH=$(pwd)
python -m pdb scripts/database/run_migrations.py

# SQL scripts
psql $DATABASE_URL -e -f scripts/security/rls_vulnerability_tests.sql

# Node.js scripts
DEBUG=* node scripts/verification/verify_connection.js
```

## Safety Guidelines

### Production Safety

1. **Never Skip Dry Run**:
   ```bash
   # Always do this first
   python scripts/database/run_migrations.py --dry-run
   ```

2. **Backup Before Changes**:
   ```bash
   # Backup database
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Use Transactions**:
   ```sql
   -- In SQL scripts
   BEGIN;
   -- Your changes
   ROLLBACK; -- or COMMIT if sure
   ```

4. **Monitor After Deployment**:
   ```bash
   # Watch logs
   tail -f logs/application.log
   
   # Check metrics
   python scripts/benchmarks/dragonfly_performance.py --quick
   ```

### Security Practices

1. **No Credentials in Code**:
   ```python
   # ✗ Bad
   db_url = "postgresql://user:password@host/db"
   
   # ✓ Good
   db_url = os.environ.get('DATABASE_URL')
   ```

2. **Validate Input**:
   ```python
   # Always validate script arguments
   if not args.table_name.isidentifier():
       raise ValueError("Invalid table name")
   ```

3. **Use Least Privilege**:
   ```bash
   # Development: limited permissions
   export DATABASE_URL=$DEV_DATABASE_URL
   
   # Production: only when needed
   export DATABASE_URL=$PROD_DATABASE_URL
   ```

### Emergency Procedures

If something goes wrong:

1. **Stop the Script**: `Ctrl+C`

2. **Check Status**:
   ```bash
   python scripts/verification/validate_schema_consistency.py
   ```

3. **Rollback if Needed**:
   ```bash
   # Database rollback
   psql $DATABASE_URL -f rollback_script.sql
   
   # Git rollback
   git checkout -- .
   ```

4. **Get Help**:
   - Check logs: `logs/`
   - Review this guide
   - Contact team lead
   - Check runbooks in `docs/runbooks/`

## Additional Resources

- [Database Schema Docs](../docs/database/schema.md)
- [API Documentation](../docs/api/README.md)
- [Deployment Guide](../docs/deployment/README.md)
- [Troubleshooting Guide](../docs/troubleshooting/README.md)
- [Security Best Practices](../docs/security/best-practices.md)

## Script Development Guidelines

When creating new scripts:

1. **Use Template Structure** (see main README)
2. **Include Help Text**: Use argparse with descriptions
3. **Add Error Handling**: Catch and log exceptions
4. **Support Dry Run**: Where applicable
5. **Write Tests**: Add to `/tests/scripts/`
6. **Document Usage**: Update relevant README files
7. **Consider Security**: Validate inputs, use env vars

Remember: Scripts should make tasks easier and safer, not more complex!