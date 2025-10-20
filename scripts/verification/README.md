# Verification Scripts

Health check and verification scripts for validating system components and connections.

## Overview

Verification scripts ensure all system components are properly configured and accessible. These scripts are essential for:

- Development environment setup
- Pre-deployment checks
- Post-deployment validation
- Troubleshooting connection issues
- Continuous monitoring

## Core Scripts

### verify_connection.py

Verify PostgreSQL database connectivity and basic operations.

**Checks**:

- Database connection
- Authentication
- Basic CRUD operations
- Connection pooling
- SSL/TLS configuration

**Usage**:

```bash
# Basic connection test
python scripts/verification/verify_connection.py

# Verbose output with timing
python scripts/verification/verify_connection.py --verbose

# Test specific operations
python scripts/verification/verify_connection.py --test-operations

# Custom connection string
python scripts/verification/verify_connection.py --database-url "postgresql://..."
```

### verify_connection.js

Node.js version for frontend developers to verify database connectivity.

**Purpose**: Validate that frontend can connect to Supabase/PostgreSQL.

**Features**:

- Supabase client testing
- Realtime subscription verification
- Auth flow testing
- RLS policy validation

**Usage**:

```bash
# Basic test
node scripts/verification/verify_connection.js

# Test specific features
node scripts/verification/verify_connection.js --test-auth --test-realtime

# Use different environment
NODE_ENV=staging node scripts/verification/verify_connection.js
```

### verify_dragonfly.py

Test DragonflyDB cache connectivity and performance.

**Validates**:

- Connection establishment
- Authentication (if configured)
- Basic operations (GET, SET, DEL)
- JSON operations
- Pub/Sub functionality
- Performance benchmarks

**Usage**:

```bash
# Basic verification
python scripts/verification/verify_dragonfly.py

# Include performance tests
python scripts/verification/verify_dragonfly.py --benchmark

# Test specific features
python scripts/verification/verify_dragonfly.py --test-json --test-pubsub

# Custom Redis URL
python scripts/verification/verify_dragonfly.py --redis-url "redis://localhost:6379"
```

### verify_extensions.py

Validate that required PostgreSQL extensions are installed and configured.

**Checks**:

- Extension availability
- Version compatibility
- Configuration parameters
- Function availability
- Performance impact

**Required Extensions**:

- `uuid-ossp`: UUID generation
- `pgcrypto`: Cryptographic functions
- `pg_trgm`: Trigram similarity search
- `pg_stat_statements`: Query performance monitoring

**Usage**:

```bash
# Verify all required extensions
python scripts/verification/verify_extensions.py

# Check specific extensions
python scripts/verification/verify_extensions.py --extensions "uuid-ossp,pgcrypto"

# Include optional extensions
python scripts/verification/verify_extensions.py --include-optional
```

### validate_schema_consistency.py

Ensure database schema matches expected structure.

**Validates**:

- Table existence and structure
- Column types and constraints
- Indexes and performance
- Foreign key relationships
- RLS policies
- Function definitions

**Usage**:

```bash
# Full schema validation
python scripts/verification/validate_schema_consistency.py

# Check specific tables
python scripts/verification/validate_schema_consistency.py --tables users,trips

# Compare with schema file
python scripts/verification/validate_schema_consistency.py --schema-file schema.sql

# Generate schema diff
python scripts/verification/validate_schema_consistency.py --diff
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Verify Deployment

on:
  deployment_status:
    types: [completed]

jobs:
  verify:
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          uv sync --frozen
          
      - name: Verify Database
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python scripts/verification/verify_connection.py
          python scripts/verification/verify_extensions.py
          python scripts/verification/validate_schema_consistency.py
          
      - name: Verify Cache
        env:
          REDIS_URL: ${{ secrets.REDIS_URL }}
        run: |
          python scripts/verification/verify_dragonfly.py --benchmark
```

## Health Check Endpoints

These scripts can be wrapped as HTTP endpoints for monitoring:

```python
# Example Flask endpoint
@app.route('/health/database')
def health_database():
    try:
        result = verify_database_connection()
        return jsonify({"status": "healthy", "details": result}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
```

## Troubleshooting Guide

### Common Issues

1. **Connection Timeout**

   ```bash
   # Increase timeout
   python scripts/verification/verify_connection.py --timeout 30
   
   # Check network connectivity
   nc -zv database.host.com 5432
   ```

2. **Authentication Failures**

   ```bash
   # Verify credentials
   echo $DATABASE_URL | grep -o 'postgresql://[^:]*'
   
   # Test with explicit credentials
   python scripts/verification/verify_connection.py \
     --username myuser --password mypass --host localhost
   ```

3. **SSL/TLS Issues**

   ```bash
   # Disable SSL for testing (not for production!)
   python scripts/verification/verify_connection.py --no-ssl
   
   # Verify SSL certificate
   openssl s_client -connect database.host.com:5432
   ```

4. **Extension Not Found**

   ```sql
   -- Check available extensions
   SELECT * FROM pg_available_extensions WHERE name LIKE '%uuid%';
   
   -- Install missing extension (requires superuser)
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

## Performance Benchmarks

### Expected Results

**Database Connection**:

- Connection time: < 100ms
- Simple query: < 10ms
- Complex query: < 100ms
- Connection pool efficiency: > 90%

**Cache Operations**:

- SET operation: < 1ms
- GET operation: < 1ms
- JSON operations: < 2ms
- Pub/Sub latency: < 5ms

**Schema Validation**:

- Full validation: < 5 seconds
- Per-table validation: < 100ms

## Monitoring Integration

### Prometheus Metrics

```python
# Example metrics exposed by verification scripts
database_connection_status{environment="production"} 1
database_response_time_ms{operation="select"} 8.5
cache_connection_status{service="dragonfly"} 1
cache_operation_latency_ms{operation="get"} 0.8
schema_validation_passed{table="users"} 1
extensions_installed{name="uuid-ossp"} 1
```

### Logging

All verification scripts use structured logging:

```json
{
  "timestamp": "2025-06-17T10:30:00Z",
  "level": "INFO",
  "script": "verify_connection.py",
  "event": "connection_established",
  "duration_ms": 45,
  "details": {
    "host": "db.example.com",
    "port": 5432,
    "database": "tripsage",
    "ssl": true
  }
}
```

## Best Practices

1. **Run in Order**: Some scripts depend on others

   ```bash
   # Recommended order
   1. verify_connection.py
   2. verify_extensions.py
   3. validate_schema_consistency.py
   4. verify_dragonfly.py
   ```

2. **Use in Development**: Run before starting development

   ```bash
   # Add to your dev setup script
   python scripts/verification/verify_connection.py || exit 1
   python scripts/verification/verify_dragonfly.py || exit 1
   ```

3. **Automate Checks**: Include in deployment pipelines

   ```bash
   # Pre-deployment
   make verify-infrastructure
   
   # Post-deployment
   make verify-deployment
   ```

4. **Regular Monitoring**: Schedule periodic checks

   ```cron
   # Run every 5 minutes
   */5 * * * * /app/scripts/verification/verify_all.sh
   ```

## Related Documentation

- [Infrastructure Setup Guide](../../docs/infrastructure/setup.md)
- [Monitoring and Alerts](../../docs/monitoring/README.md)
- [Troubleshooting Guide](../../docs/troubleshooting/README.md)
