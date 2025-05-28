# Migration Rollbacks

This directory contains rollback SQL files that can undo the changes made by corresponding forward migrations.

## Contents

- `20250508_06_rollback.sql`: General rollback statements for the initial schema migrations
- `20250522_01_add_chat_session_tables_rollback.sql`: Rollback for chat session tables
- `20250526_01_enable_pgvector_extensions_rollback.sql`: Rollback for pgvector extensions

## Purpose

Rollback files provide SQL statements to:
- Undo schema changes made by migrations
- Remove tables, indexes, and constraints added by migrations
- Restore the database to a previous state when needed

## Important Notes

- **These files are NOT automatically executed**
- They must be run manually when rollback is needed
- Always backup your database before running rollback scripts
- Review the rollback script carefully before execution
- Some rollbacks may result in data loss (dropping tables, etc.)

## Usage

To rollback a migration:

1. **Backup your database first**
2. Review the rollback script to understand what will be undone
3. Run the rollback script manually:
   ```sql
   \i migrations/rollbacks/filename_rollback.sql
   ```
4. Verify the rollback was successful
5. Update your migration tracking if needed

## Naming Convention

Rollback files follow the pattern:
```
YYYYMMDD_NN_description_rollback.sql
```

This matches the corresponding forward migration filename with `_rollback` suffix. 