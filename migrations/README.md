# TripSage Database Migrations

This directory contains SQL migration files that define the database schema for the TripSage application.

## Migration Files

Migrations are applied in the order of their filenames. The naming convention is:

```plaintext
YYYYMMDD_NN_description.sql
```

Where:

- `YYYYMMDD` is the date the migration was created
- `NN` is a two-digit sequence number for that day (starting at 01)
- `description` is a brief description of the migration

## Migration Structure

Each migration file should:

1. Begin with a header comment indicating the migration name, description, and creation date
2. Contain idempotent SQL statements when possible
3. Use `IF NOT EXISTS` and `IF EXISTS` clauses to prevent errors on repeated runs
4. Include comments for tables and columns
5. Define constraints, indexes, and relationships as needed

## Running Migrations

There are several ways to run migrations:

### 1. Using the Script

Run the `run_migrations.py` script:

```bash
# Run all pending migrations
python scripts/run_migrations.py

# Dry run (show what would be applied without making changes)
python scripts/run_migrations.py --dry-run

# Run migrations up to a specific file
python scripts/run_migrations.py --up-to 20250508_03_complex_relationship_tables.sql
```

### 2. Using the API (Admin Only)

For authenticated admin users, migrations can be run via the API:

```bash
# Get current migration status
curl -X GET "http://localhost:8000/api/admin/migrations/status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Run migrations
curl -X POST "http://localhost:8000/api/admin/migrations/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"dry_run": false}'
```

### 3. Programmatically

```python
from src.db.migrations import run_migrations

# Run all pending migrations
succeeded, failed = run_migrations()

# Dry run
succeeded, failed = run_migrations(dry_run=True)

# Run up to a specific migration
succeeded, failed = run_migrations(up_to="20250508_03_complex_relationship_tables.sql")
```

## Creating New Migrations

1. Create a new SQL file following the naming convention
2. Include a header comment with name, description, and date
3. Write your SQL statements
4. Test the migration with `--dry-run` before applying
5. Consider adding a corresponding rollback statement to `20250508_06_rollback.sql`

## Migration Tracking

Migrations are tracked in a `migrations` table created in the database. This table contains:

- `id`: Primary key
- `filename`: Name of the migration file
- `applied_at`: Timestamp when the migration was applied

## Important Tables

The main tables in the schema are:

1. `users`: User accounts and preferences
2. `trips`: Travel trip details and planning information
3. `flights`: Flight options for trips
4. `accommodations`: Accommodation options for trips
5. `transportation`: Transportation options for trips
6. `itinerary_items`: Items in a trip itinerary
7. `search_parameters`: Search parameters used for finding travel options
8. `price_history`: Historical price data for travel options
9. `saved_options`: Saved travel options for comparison
10. `trip_notes`: Notes attached to trips
11. `trip_comparison`: Comparison data between different trip options
