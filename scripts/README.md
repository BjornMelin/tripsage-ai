# TripSage Scripts Documentation

> **⚡ Quick Start:** Run `python scripts/testing/test_runner.py` to verify your environment is set up correctly.

## Overview

This directory contains automation scripts and utilities for managing the TripSage platform. Scripts are organized by functional area to support development, deployment, testing, and operations.

### 🎯 Purpose
- **Automation**: Reduce manual tasks and ensure consistency
- **Operations**: Database management, service deployment, and monitoring
- **Development**: Testing utilities, benchmarking, and verification tools
- **Security**: Vulnerability testing and security validations

## 📁 Directory Structure

### `/automation/` - Deployment & Configuration Scripts

Automated deployment and configuration management tools.

| Script | Purpose | Requirements |
|--------|---------|-------------|
| `deploy_extensions.py` | Deploy Supabase extensions and automation features | `asyncpg`, Supabase access |

### `/database/` - Database Management

Database initialization, migration, and infrastructure management.

| Script | Purpose | Usage |
|--------|---------|-------|
| `init_database.py` | Initialize database schema and base data | `python scripts/database/init_database.py` |
| `run_migrations.py` | Apply pending SQL migrations | `python scripts/database/run_migrations.py [--dry-run]` |
| `deploy_storage_infrastructure.py` | Deploy storage buckets and policies | `python scripts/database/deploy_storage_infrastructure.py` |
| `deploy_triggers.py` | Deploy database triggers and functions | `python scripts/database/deploy_triggers.py` |

**Migrations Directory**: `/database/migrations/`
- SQL files with timestamp prefixes (e.g., `20250615_remove_bigint_add_uuid_only.sql`)
- Applied in chronological order
- Track applied migrations in `migration_history` table

### `/benchmarks/` - Comprehensive Performance Testing

Unified performance benchmarking suite for database, vector search, and cache optimization validation.

| Script | Purpose | Metrics |
|--------|---------|--------|
| `run_benchmarks.py` | Complete performance validation suite | Database, vector, cache performance |
| `benchmark_runner.py` | Core benchmark orchestration | Query latency, throughput, memory |
| `pgvector_benchmark.py` | Specialized vector search benchmarking | 30x improvement validation |
| `dragonfly_performance.py` | Cache performance testing | Throughput, latency, memory usage |
| `regression_detector.py` | Performance regression detection | Statistical analysis, baselines |

### `/security/` - Security Testing

Security validation and vulnerability testing scripts.

| Script | Purpose | Output |
|--------|---------|--------|
| `security_validation.py` | Comprehensive security audit | Security findings report |
| `rls_vulnerability_tests.sql` | Test Row Level Security policies | RLS policy audit |

### `/testing/` - Test Utilities

Test execution and analysis tools. See [Testing README](./testing/README.md) for details.

| Script | Purpose | Features |
|--------|---------|----------|
| `run_tests_with_coverage.py` | Run full test suite with coverage | HTML reports, failure analysis |
| `test_summary.py` | Generate test summary reports | Cross-directory analysis |
| `test_runner.py` | Quick smoke tests | Import verification, basic checks |
| `activate-websocket.js` | WebSocket feature activation testing | Real-time connection validation |
| `test-websocket.js` | WebSocket functionality testing | Connection and message flow tests |

### `/verification/` - Service Health Checks

Connection verification and health check scripts.

| Script | Purpose | Environment |
|--------|---------|-------------|
| `verify_connection.py` | Verify database connectivity (Python) | Production/Development |
| `verify_connection.js` | Verify database connectivity (Node.js) | Frontend development |
| `verify_dragonfly.py` | Test DragonflyDB cache connection | All environments |
| `verify_extensions.py` | Validate Supabase extensions | Production deployment |
| `validate_schema_consistency.py` | Check database schema integrity | CI/CD pipeline |


## 🚀 Common Workflows

### Initial Setup

```bash
# 1. Verify environment
python scripts/testing/test_runner.py

# 2. Initialize database
python scripts/database/init_database.py

# 3. Run migrations
python scripts/database/run_migrations.py

# 4. Deploy extensions
python scripts/automation/deploy_extensions.py

# 5. Verify all connections
python scripts/verification/verify_connection.py
python scripts/verification/verify_dragonfly.py
```

### Development Workflow

```bash
# Run tests with coverage
python scripts/testing/run_tests_with_coverage.py

# Check performance (comprehensive)
python scripts/benchmarks/run_benchmarks.py quick-test

# Check cache performance specifically
python scripts/benchmarks/dragonfly_performance.py --quick

# Validate security
python scripts/security/security_validation.py
```

### Deployment Checklist

```bash
# 1. Run migrations (dry run first)
python scripts/database/run_migrations.py --dry-run
python scripts/database/run_migrations.py

# 2. Deploy infrastructure
python scripts/database/deploy_storage_infrastructure.py
python scripts/database/deploy_triggers.py

# 3. Verify deployment
python scripts/verification/validate_schema_consistency.py
python scripts/verification/verify_extensions.py
```

## 📋 Prerequisites

### Environment Setup

1. **Python 3.12+** with virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Node.js 18+** for JavaScript scripts:
   ```bash
   npm install
   ```

3. **Environment Variables** (`.env` file):
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/tripsage
   REDIS_URL=redis://localhost:6379
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   ```

### Required Services

- **PostgreSQL 15+** (via Supabase or local)
- **DragonflyDB** or Redis 7+
- **Supabase Project** (for production features)

## 🔒 Security Considerations

1. **Credentials**: Never commit credentials. Use environment variables.
2. **Permissions**: Scripts require appropriate database permissions:
   - Migration scripts need DDL permissions
   - Verification scripts need read permissions
   - Deployment scripts need admin permissions
3. **Audit**: Run `security_validation.py` before deployments
4. **RLS Testing**: Use `security/rls_vulnerability_tests.sql` to validate policies

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**:
   - Ensure you're running from project root
   - Verify virtual environment is activated
   - Check `PYTHONPATH` includes project root

2. **Connection Failures**:
   - Verify environment variables are set
   - Check service is running (PostgreSQL, DragonflyDB)
   - Test with verification scripts first

3. **Migration Failures**:
   - Always run with `--dry-run` first
   - Check migration history table
   - Review migration SQL for conflicts

### Debug Mode

Most scripts support verbose/debug output:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python scripts/database/run_migrations.py
```

## 📚 Related Documentation

- [Database Schema Documentation](../docs/database/schema.md)
- [API Documentation](../docs/api/README.md)
- [Testing Guide](./testing/README.md)
- [Deployment Guide](../docs/deployment/README.md)

## 🤝 Contributing

When adding new scripts:

1. Follow the established directory structure
2. Include comprehensive docstrings
3. Add error handling and logging
4. Update this README with script details
5. Add corresponding tests in `/tests/`
6. Consider security implications

### Script Template

```python
#!/usr/bin/env python3
"""Script purpose and description.

Usage:
    python scripts/category/script_name.py [options]

Requirements:
    - List required services
    - List required permissions
    - List environment variables
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main script logic."""
    parser = argparse.ArgumentParser(description=__doc__)
    # Add arguments
    args = parser.parse_args()
    
    try:
        # Script logic here
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```
