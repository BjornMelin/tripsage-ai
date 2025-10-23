# Automation Scripts

This directory contains scripts for automating deployment, configuration, and infrastructure management tasks.

## Overview

Automation scripts help maintain consistency across environments and reduce manual deployment errors. These scripts handle tasks that would otherwise require multiple manual steps or complex configurations.

## Scripts

### deploy_extensions.py

Deploy and configure Supabase extensions with automated error handling and rollback capabilities.

**Purpose**: Automates the deployment of PostgreSQL extensions and related configurations in Supabase.

**Features**:

- Automatic dependency resolution
- Transaction-based deployment with rollback
- Progress tracking with rich console output
- Idempotent operations (safe to run multiple times)

**Usage**:

```bash
python scripts/automation/deploy_extensions.py [options]

Options:
  --database-url URL    Override database URL from environment
  --schema-path PATH    Path to schema files (default: ./schema)
  --dry-run            Show what would be deployed without executing
  --extensions LIST     Comma-separated list of extensions to deploy
```

**Prerequisites**:

- Supabase project with appropriate permissions
- Python packages: `asyncpg`, `rich`
- Environment variables:
  - `DATABASE_URL` or `SUPABASE_DB_URL`
  - `SUPABASE_PROJECT_ID` (optional)

**Example**:

```bash
# Deploy all extensions
python scripts/automation/deploy_extensions.py

# Deploy specific extensions
python scripts/automation/deploy_extensions.py --extensions "uuid-ossp,pgcrypto,pg_trgm"

# Dry run to see what would be deployed
python scripts/automation/deploy_extensions.py --dry-run
```

## Best Practices

1. **Always test in development first**: Run automation scripts in a development environment before production.

2. **Use dry-run mode**: Most scripts support `--dry-run` to preview changes without applying them.

3. **Check logs**: Scripts produce detailed logs. Review them for warnings or errors:

   ```bash
   python scripts/automation/deploy_extensions.py 2>&1 | tee deploy.log
   ```

4. **Version control**: Keep track of when scripts were run and what changes were made.

5. **Rollback plan**: Understand how to rollback changes if needed. Most scripts include rollback procedures.

## Error Handling

Scripts in this directory follow these error handling principles:

- **Graceful failures**: Scripts catch and log errors without crashing
- **Rollback on error**: Database operations use transactions
- **Clear error messages**: Errors include context and suggested fixes
- **Exit codes**: Scripts return appropriate exit codes for CI/CD integration

## Security

- Scripts use environment variables for sensitive data
- No credentials are hardcoded
- All database operations use parameterized queries
- Audit logs are generated for compliance

## Adding New Automation Scripts

When creating new automation scripts:

1. Follow the existing naming convention: `deploy_<feature>.py` or `configure_<service>.py`
2. Include docstrings and CLI help
3. Implement dry-run mode where applicable
4. Use logging for all operations
5. Handle errors gracefully with rollback capabilities
6. Add unit tests in `/tests/scripts/automation/`

## Dependencies

Common dependencies for automation scripts:

```txt
asyncpg>=0.29.0      # Async PostgreSQL driver
rich>=13.0.0         # Terminal formatting
click>=8.0.0         # CLI framework
pydantic>=2.0.0      # Configuration validation
```

## Monitoring and Alerts

For production deployments:

1. **Log aggregation**: Scripts send logs to centralized logging
2. **Metrics**: Key operations emit metrics for monitoring
3. **Alerts**: Failed deployments trigger alerts
4. **Audit trail**: All changes are recorded with timestamp and user

## Related Documentation

- [Database Migration Guide](../database/README.md)
- [Deployment Best Practices](../../docs/deployment/best-practices.md)
- [Infrastructure as Code](../../docs/infrastructure/README.md)
