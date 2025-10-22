#!/usr/bin/env python3
"""Schema Consistency Validation Script.

Validates that all database schema files follow consistent patterns:
- All user_id fields are UUID type with foreign key constraints
- All foreign key constraints are properly defined
- No TEXT fields are used for UUID storage
- Schema files match migration expectations
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SchemaIssue:
    """Represents a schema consistency issue."""

    file_path: str
    line_number: int
    issue_type: str
    description: str
    severity: str  # 'error', 'warning', 'info'


@dataclass
class TableDefinition:
    """Represents a parsed table definition."""

    name: str
    file_path: str
    line_number: int
    columns: dict[str, str]  # column_name -> column_type
    foreign_keys: list[tuple[str, str]]  # (column, references)


class SchemaValidator:
    """Validates PostgreSQL schema files for consistency."""

    def __init__(self, schema_dir: str):
        """Initialize schema validator."""
        self.schema_dir = Path(schema_dir)
        self.issues: list[SchemaIssue] = []
        self.tables: dict[str, TableDefinition] = {}

    def validate(self) -> bool:
        """Run all validation checks."""
        print("Starting schema consistency validation...")

        # Find and parse all SQL files
        sql_files = list(self.schema_dir.glob("*.sql"))
        print(f"Found {len(sql_files)} SQL files to validate")

        # Parse table definitions
        for sql_file in sql_files:
            self._parse_sql_file(sql_file)

        # Run validation checks
        self._validate_user_id_consistency()
        self._validate_foreign_keys()
        self._validate_no_text_uuids()
        self._validate_migration_consistency()

        # Report results
        return self._report_results()

    def _parse_sql_file(self, file_path: Path):
        """Parse SQL file for table definitions."""
        with file_path.open() as f:
            content = f.read()
            lines = content.split("\n")

        # Find CREATE TABLE statements
        table_pattern = re.compile(
            r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\(", re.IGNORECASE
        )
        column_pattern = re.compile(r"^\s*(\w+)\s+(\w+(?:\([^)]+\))?)", re.IGNORECASE)
        fk_pattern = re.compile(r"REFERENCES\s+(\w+\.?\w*)\s*\((\w+)\)", re.IGNORECASE)

        i = 0
        while i < len(lines):
            line = lines[i]
            table_match = table_pattern.search(line)

            if table_match:
                table_name = table_match.group(1)
                table_def = TableDefinition(
                    name=table_name,
                    file_path=str(file_path),
                    line_number=i + 1,
                    columns={},
                    foreign_keys=[],
                )

                # Parse columns until we hit the closing parenthesis
                i += 1
                while i < len(lines) and ");" not in lines[i]:
                    col_line = lines[i]
                    col_match = column_pattern.match(col_line)

                    if col_match:
                        col_name = col_match.group(1)
                        col_type = col_match.group(2)

                        # Skip constraint definitions
                        constraint_keywords = [
                            "CONSTRAINT",
                            "PRIMARY",
                            "UNIQUE",
                            "CHECK",
                            "FOREIGN",
                        ]
                        if col_name.upper() not in constraint_keywords:
                            table_def.columns[col_name] = col_type

                            # Check for foreign key
                            fk_match = fk_pattern.search(col_line)
                            if fk_match:
                                ref_table = fk_match.group(1)
                                ref_column = fk_match.group(2)
                                # Handle schema-qualified references (e.g., auth.users)
                                full_ref = f"{ref_table}({ref_column})"
                                table_def.foreign_keys.append((col_name, full_ref))

                    i += 1

                self.tables[table_name] = table_def

            i += 1

    def _validate_user_id_consistency(self):
        """Validate that all user_id fields are UUID with proper foreign keys."""
        print("\n✅ Validating user_id field consistency...")

        for table_name, table_def in self.tables.items():
            if "user_id" in table_def.columns:
                col_type = table_def.columns["user_id"].upper()

                # Check if it's UUID type
                if "UUID" not in col_type:
                    self.issues.append(
                        SchemaIssue(
                            file_path=table_def.file_path,
                            line_number=table_def.line_number,
                            issue_type="incorrect_type",
                            description=(
                                f"Table '{table_name}' has user_id of type "
                                f"'{col_type}' instead of UUID"
                            ),
                            severity="error",
                        )
                    )

                # Check for foreign key constraint
                has_fk = any(
                    fk[0] == "user_id" and ("auth.users" in fk[1] or "auth" in fk[1])
                    for fk in table_def.foreign_keys
                )

                if not has_fk:
                    # Some tables might not need FK to auth.users (e.g., search cache)
                    search_cache_tables = [
                        "search_destinations",
                        "search_activities",
                        "search_flights",
                        "search_hotels",
                    ]
                    if table_name not in search_cache_tables:
                        self.issues.append(
                            SchemaIssue(
                                file_path=table_def.file_path,
                                line_number=table_def.line_number,
                                issue_type="missing_foreign_key",
                                description=(
                                    f"Table '{table_name}' user_id lacks foreign key "
                                    f"to auth.users(id)"
                                ),
                                severity="warning",
                            )
                        )

    def _validate_foreign_keys(self):
        """Validate that all foreign key references use consistent types."""
        print("✅ Validating foreign key consistency...")

        for table_name, table_def in self.tables.items():
            for col_name, ref in table_def.foreign_keys:
                # Parse reference
                ref_match = re.match(r"(\w+)\.?(\w+)?\((\w+)\)", ref)
                if ref_match:
                    ref_table = ref_match.group(1)
                    ref_column = ref_match.group(3)

                    # Skip auth schema references
                    if ref_table == "auth":
                        continue

                    # Check if referenced table exists in our parsed tables
                    if ref_table in self.tables:
                        ref_table_def = self.tables[ref_table]
                        if ref_column in ref_table_def.columns:
                            # Compare types
                            col_type = table_def.columns.get(col_name, "").upper()
                            ref_type = ref_table_def.columns.get(ref_column, "").upper()

                            # Normalize types for comparison
                            col_type_base = col_type.split()[0]
                            ref_type_base = ref_type.split()[0]

                            if col_type_base != ref_type_base:
                                self.issues.append(
                                    SchemaIssue(
                                        file_path=table_def.file_path,
                                        line_number=table_def.line_number,
                                        issue_type="type_mismatch",
                                        description=(
                                            f"FK type mismatch: {table_name}."
                                            f"{col_name} ({col_type}) → "
                                            f"{ref_table}.{ref_column} ({ref_type})"
                                        ),
                                        severity="error",
                                    )
                                )

    def _validate_no_text_uuids(self):
        """Validate that no TEXT fields are used for UUID storage."""
        print("✅ Validating no TEXT fields used for UUIDs...")

        uuid_pattern = re.compile(r"(.*_id|uuid|guid)", re.IGNORECASE)

        for table_name, table_def in self.tables.items():
            for col_name, col_type in table_def.columns.items():
                if (
                    uuid_pattern.match(col_name)
                    and "TEXT" in col_type.upper()
                    and col_name not in ["external_id", "tool_id"]
                ):
                    self.issues.append(
                        SchemaIssue(
                            file_path=table_def.file_path,
                            line_number=table_def.line_number,
                            issue_type="text_uuid",
                            description=(
                                f"Column {table_name}.{col_name} uses TEXT type "
                                f"but appears to be a UUID field"
                            ),
                            severity="warning",
                        )
                    )

    def _validate_migration_consistency(self):
        """Validate that migration file references all schema files."""
        print("✅ Validating migration file consistency...")

        migration_file = (
            self.schema_dir.parent
            / "migrations"
            / "20250609_02_consolidated_production_schema.sql"
        )
        if migration_file.exists():
            with migration_file.open() as f:
                migration_content = f.read()

            # Check that all schema files are referenced
            for sql_file in self.schema_dir.glob("*.sql"):
                file_ref = f"\\i schemas/{sql_file.name}"
                if file_ref not in migration_content:
                    self.issues.append(
                        SchemaIssue(
                            file_path=str(migration_file),
                            line_number=0,
                            issue_type="missing_schema_reference",
                            description=(
                                f"Migration doesn't reference schema file: "
                                f"{sql_file.name}"
                            ),
                            severity="warning",
                        )
                    )

    def _report_results(self) -> bool:
        """Report validation results."""
        print("\n" + "=" * 60)
        print("SCHEMA VALIDATION RESULTS")
        print("=" * 60)

        if not self.issues:
            print("✅ All schema consistency checks passed!")
            sql_files = len(list(self.schema_dir.glob("*.sql")))
            print(f"Validated {len(self.tables)} tables across {sql_files} files")
            return True

        # Group issues by severity
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        print(f"\n❌ Found {len(self.issues)} issues:")
        print(f"  - {len(errors)} errors")
        print(f"  - {len(warnings)} warnings")
        print(f"  - {len(info)} info messages")

        # Display issues by severity
        if errors:
            print("\nERRORS:")
            for issue in errors:
                print(f"  {issue.file_path}:{issue.line_number}")
                print(f"    [{issue.issue_type}] {issue.description}")

        if warnings:
            print("\n⚠️  WARNINGS:")
            for issue in warnings:
                print(f"  {issue.file_path}:{issue.line_number}")
                print(f"    [{issue.issue_type}] {issue.description}")

        if info:
            print("\nINFO:")
            for issue in info:
                print(f"  {issue.file_path}:{issue.line_number}")
                print(f"    [{issue.issue_type}] {issue.description}")

        return len(errors) == 0


def main():
    """Main entry point."""
    # Determine schema directory
    script_dir = Path(__file__).parent.parent.parent  # Go up to project root
    schema_dir = script_dir / "supabase" / "schemas"

    if not schema_dir.exists():
        print(f"❌ Schema directory not found: {schema_dir}")
        sys.exit(1)

    # Run validation
    validator = SchemaValidator(str(schema_dir))
    success = validator.validate()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
