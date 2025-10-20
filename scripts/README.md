# TripSage Scripts

> **⚡ Quick Start:** `python scripts/testing/test_runner.py` to verify environment setup.

Automation scripts and utilities for TripSage development, deployment, and operations. Organized by functional area for easy discovery and maintenance.

## Directory Structure

### `/automation/` - Deployment Scripts

- **`deploy_extensions.py`** - Deploy Supabase extensions and automation features

### `/database/` - Database Management

- **`init_database.py`** - Initialize database schema and seed data
- **`run_migrations.py`** - Apply pending SQL migrations (supports `--dry-run`)
- **`deploy_storage_infrastructure.py`** - Deploy storage buckets and policies
- **`deploy_triggers.py`** - Deploy database triggers and functions
- **`migrations/`** - SQL migration files with timestamp prefixes

### `/benchmarks/` - Performance Testing

- **`benchmark.py`** - Unified performance testing suite
- **`config.py`** - Benchmark configuration and settings
- **`collectors.py`** - Metrics collection and reporting

### `/security/` - Security Validation

- **`security_validation.py`** - Vulnerability testing and security audits
- **`rls_vulnerability_tests.sql`** - RLS policy validation tests

### `/testing/` - Test Utilities

- **`test_runner.py`** - Main test execution and environment validation
- **`run_tests_with_coverage.py`** - Test execution with coverage reporting

### `/verification/` - Connection & Health Checks

- **`verify_connection.py`** - Database connection validation
- **`verify_dragonfly.py`** - DragonflyDB connection and performance testing
- **`verify_extensions.py`** - Extension functionality verification
- **`validate_schema_consistency.py`** - Schema validation across environments

## Common Workflows

### Environment Setup

```bash
# 1. Initialize database
python scripts/database/init_database.py

# 2. Apply migrations
python scripts/database/run_migrations.py

# 3. Deploy extensions
python scripts/automation/deploy_extensions.py

# 4. Verify setup
python scripts/verification/verify_connection.py
python scripts/verification/verify_dragonfly.py
```

### Development Workflow

```bash
# Run tests with coverage
python scripts/testing/run_tests_with_coverage.py

# Validate security
python scripts/security/security_validation.py

# Performance benchmarking
python scripts/benchmarks/benchmark.py --quick
```

### Performance Testing

```bash
# Quick benchmark suite
python scripts/benchmarks/benchmark.py --iterations=50 --concurrent=5

# Comprehensive benchmarks
python scripts/benchmarks/benchmark.py --full-suite

# Specific benchmark types
python scripts/benchmarks/benchmark.py --database-only
python scripts/benchmarks/benchmark.py --vector-only
```

### Database Operations

```bash
# Dry-run migrations (safe preview)
python scripts/database/run_migrations.py --dry-run

# Apply migrations
python scripts/database/run_migrations.py

# Validate schema consistency
python scripts/verification/validate_schema_consistency.py
```

## Environment Variables

Core environment variables used across scripts:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@host:port/db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Cache Configuration
REDIS_URL=redis://localhost:6379
DRAGONFLY_PASSWORD=your-dragonfly-password

# Security Settings
ENABLE_RLS_VALIDATION=true
SECURITY_SCAN_DEPTH=comprehensive
```

## Dependencies

Scripts require Python 3.13+ and the following core packages:

```bash
# Install with uv (recommended)
uv add asyncpg supabase click pydantic pytest

# Or with pip
pip install asyncpg supabase click pydantic pytest
```

## Safety Guidelines

### Before Running Scripts

1. **Backup data** before running migration or database scripts
2. **Use dry-run flags** when available to preview changes
3. **Test in development** environment first
4. **Review script output** for warnings or errors

### Environment-Specific Considerations

- **Development**: Safe to run all scripts
- **Staging**: Use dry-run flags for database operations
- **Production**: Coordinate with team, use maintenance windows

## Performance Expectations

### Benchmark Targets

- **API Response Time**: <100ms (95th percentile)
- **Database Operations**: <50ms (complex queries)
- **Vector Search**: <10ms (with HNSW indexing)
- **Cache Operations**: <5ms (DragonflyDB)

### Coverage Requirements

- **Test Coverage**: ≥90% for critical paths
- **Benchmark Coverage**: All major service operations
- **Security Coverage**: All authentication and authorization flows

## Troubleshooting

### Common Issues

#### **Connection Failures**

```bash
# Check database connectivity
python scripts/verification/verify_connection.py

# Check cache connectivity  
python scripts/verification/verify_dragonfly.py
```

#### **Migration Errors**

```bash
# View pending migrations
python scripts/database/run_migrations.py --status

# Dry-run to check for issues
python scripts/database/run_migrations.py --dry-run
```

#### **Performance Issues**

```bash
# Run diagnostic benchmarks
python scripts/benchmarks/benchmark.py --diagnostics

# Check resource usage
python scripts/verification/validate_schema_consistency.py
```

### Getting Help

1. **Check script help**: Most scripts support `--help` flag
2. **Review logs**: Scripts output detailed logging for debugging
3. **Environment validation**: Run `scripts/testing/test_runner.py` first
4. **Documentation**: Each subdirectory has specific README with details

## Contributing

When adding new scripts:

1. **Follow naming conventions**: Use snake_case, descriptive names
2. **Add error handling**: Comprehensive error messages and recovery
3. **Include documentation**: Docstrings and README updates
4. **Add tests**: Minimum 90% test coverage for new functionality
5. **Use type hints**: Full typing for maintainability

### Script Template

```python
#!/usr/bin/env python3
"""
Brief description of script purpose.

Usage:
    python script_name.py [options]
"""

import asyncio
import logging
from typing import Optional

import click

logger = logging.getLogger(__name__)


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without executing")
def main(dry_run: bool) -> None:
    """Script main function."""
    try:
        # Implementation
        pass
    except Exception as e:
        logger.exception(f"Script failed: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

This consolidated documentation provides essential information while eliminating redundancy and over-engineering. For detailed implementation specifics, refer to individual script docstrings and subdirectory READMEs.
