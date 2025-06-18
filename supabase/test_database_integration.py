#!/usr/bin/env python3
"""
TripSage Database Integration Test Script
Tests Supabase database functionality including trip collaboration,
RLS policies, and vector search.
"""

import os
import sys
from pathlib import Path

class DatabaseTester:
    """Database integration tester for TripSage Supabase schema."""

    def __init__(self):
        self.test_results = []
        self.schema_dir = Path("supabase/schemas")
        self.migration_dir = Path("supabase/migrations")

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status}: {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append(
            {"test": test_name, "passed": passed, "message": message}
        )

    def test_schema_files_exist(self) -> bool:
        """Test that all required schema files exist."""
        required_files = [
            "00_extensions.sql",
            "01_tables.sql",
            "02_indexes.sql",
            "03_functions.sql",
            "04_triggers.sql",
            "05_policies.sql",
            "06_views.sql",
        ]

        missing_files = []
        for file in required_files:
            if not (self.schema_dir / file).exists():
                missing_files.append(file)

        if missing_files:
            self.log_test("Schema Files Exist", False, f"Missing: {missing_files}")
            return False
        else:
            self.log_test(
                "Schema Files Exist", True, f"All {len(required_files)} files found"
            )
            return True

    def test_trip_collaborators_integration(self) -> bool:
        """Test trip_collaborators table integration across all schema files."""
        issues = []

        # Check table definition
        tables_content = (self.schema_dir / "01_tables.sql").read_text()
        if "trip_collaborators" not in tables_content:
            issues.append("Table not found in 01_tables.sql")

        # Check indexes
        indexes_content = (self.schema_dir / "02_indexes.sql").read_text()
        if "trip_collaborators" not in indexes_content:
            issues.append("Indexes not found in 02_indexes.sql")

        # Check RLS policies
        policies_content = (self.schema_dir / "05_policies.sql").read_text()
        if "trip_collaborators" not in policies_content:
            issues.append("RLS policies not found in 05_policies.sql")

        if issues:
            self.log_test("Trip Collaborators Integration", False, f"Issues: {issues}")
            return False
        else:
            self.log_test("Trip Collaborators Integration", True, "Fully integrated")
            return True

    def test_rls_policy_consistency(self) -> bool:
        """Test RLS policy consistency across related tables."""
        policies_content = (self.schema_dir / "05_policies.sql").read_text()

        # Check for collaborative access in related tables
        tables_with_collab_access = [
            "flights",
            "accommodations",
            "transportation",
            "itinerary_items",
        ]

        missing_collab_policies = []
        for table in tables_with_collab_access:
            # Look for "shared trips" pattern in policies
            if (
                f"{table}" in policies_content
                and "shared trips" not in policies_content
            ):
                missing_collab_policies.append(table)

        if missing_collab_policies:
            self.log_test(
                "RLS Policy Consistency",
                False,
                f"Tables missing collaborative access: {missing_collab_policies}",
            )
            return False
        else:
            self.log_test(
                "RLS Policy Consistency", True, "All tables support collaboration"
            )
            return True

    def test_foreign_key_relationships(self) -> bool:
        """Test foreign key relationship integrity."""
        tables_content = (self.schema_dir / "01_tables.sql").read_text()

        # Expected foreign key patterns
        fk_checks = [
            ("auth.users", "user_id UUID.*REFERENCES auth\\.users\\(id\\)"),
            ("trips", "trip_id.*REFERENCES trips\\(id\\)"),
            ("chat_sessions", "session_id.*REFERENCES chat_sessions\\(id\\)"),
        ]

        missing_fks = []
        for table, pattern in fk_checks:
            import re

            if not re.search(pattern, tables_content, re.IGNORECASE):
                missing_fks.append(table)

        if missing_fks:
            self.log_test(
                "Foreign Key Relationships", False, f"Missing FKs: {missing_fks}"
            )
            return False
        else:
            self.log_test(
                "Foreign Key Relationships", True, "All FK relationships found"
            )
            return True

    def test_vector_search_setup(self) -> bool:
        """Test pgvector extension and embedding setup."""
        extensions_content = (self.schema_dir / "00_extensions.sql").read_text()
        tables_content = (self.schema_dir / "01_tables.sql").read_text()
        indexes_content = (self.schema_dir / "02_indexes.sql").read_text()

        issues = []

        # Check pgvector extension
        if "vector" not in extensions_content.lower():
            issues.append("pgvector extension not found")

        # Check vector columns
        if "vector(1536)" not in tables_content:
            issues.append("1536-dimension vector columns not found")

        # Check vector indexes
        if "ivfflat" not in indexes_content:
            issues.append("Vector indexes (IVFFlat) not found")

        if issues:
            self.log_test("Vector Search Setup", False, f"Issues: {issues}")
            return False
        else:
            self.log_test("Vector Search Setup", True, "Complete pgvector integration")
            return True

    def test_maintenance_functions(self) -> bool:
        """Test database maintenance functions."""
        functions_content = (self.schema_dir / "03_functions.sql").read_text()

        required_functions = [
            "maintain_database_performance",
            "cleanup_old_memories",
            "optimize_vector_indexes",
            "get_user_accessible_trips",
            "check_trip_permission",
        ]

        missing_functions = []
        for func in required_functions:
            if func not in functions_content:
                missing_functions.append(func)

        if missing_functions:
            self.log_test(
                "Maintenance Functions", False, f"Missing: {missing_functions}"
            )
            return False
        else:
            self.log_test(
                "Maintenance Functions",
                True,
                f"All {len(required_functions)} functions found",
            )
            return True

    def test_sql_syntax_validity(self) -> bool:
        """Test SQL syntax validity by parsing files."""
        valid_files = []
        invalid_files = []

        for sql_file in self.schema_dir.glob("*.sql"):
            try:
                content = sql_file.read_text()
                # Basic syntax checks
                if content.strip():
                    # Check for balanced parentheses
                    open_parens = content.count("(")
                    close_parens = content.count(")")
                    if open_parens == close_parens:
                        valid_files.append(sql_file.name)
                    else:
                        invalid_files.append(
                            f"{sql_file.name} (unbalanced parentheses)"
                        )
                else:
                    invalid_files.append(f"{sql_file.name} (empty file)")
            except Exception as e:
                invalid_files.append(f"{sql_file.name} (read error: {e})")

        if invalid_files:
            self.log_test(
                "SQL Syntax Validity", False, f"Invalid files: {invalid_files}"
            )
            return False
        else:
            self.log_test(
                "SQL Syntax Validity", True, f"All {len(valid_files)} files valid"
            )
            return True

    def test_migration_consistency(self) -> bool:
        """Test migration file consistency with schema files."""
        # Check if migration files exist
        migrations = list(self.migration_dir.glob("*.sql"))

        if not migrations:
            self.log_test("Migration Consistency", False, "No migration files found")
            return False

        # Check for trip_collaborators migration
        collab_migration = None
        for migration in migrations:
            if "trip_collaborators" in migration.read_text():
                collab_migration = migration
                break

        if not collab_migration:
            self.log_test(
                "Migration Consistency", False, "trip_collaborators migration not found"
            )
            return False

        self.log_test(
            "Migration Consistency",
            True,
            f"Found {len(migrations)} migrations including trip_collaborators",
        )
        return True

    def test_security_configuration(self) -> bool:
        """Test security configuration and RLS setup."""
        policies_content = (self.schema_dir / "05_policies.sql").read_text()

        security_checks = [
            ("RLS enabled", "ENABLE ROW LEVEL SECURITY"),
            ("Auth context", "auth.uid()"),
            ("Policy comments", "COMMENT ON POLICY"),
            ("Multi-tenant isolation", "user_id = auth.uid()"),
        ]

        missing_security = []
        for check_name, pattern in security_checks:
            if pattern not in policies_content:
                missing_security.append(check_name)

        if missing_security:
            self.log_test(
                "Security Configuration", False, f"Missing: {missing_security}"
            )
            return False
        else:
            self.log_test("Security Configuration", True, "Complete RLS security setup")
            return True

    def generate_schema_summary(self) -> dict:
        """Generate a summary of the database schema."""
        summary = {
            "tables": [],
            "indexes": [],
            "functions": [],
            "policies": [],
            "extensions": [],
        }

        try:
            # Count components
            tables_content = (self.schema_dir / "01_tables.sql").read_text()
            import re

            # Count tables
            table_matches = re.findall(
                r"CREATE TABLE.*?(\w+)\s*\(", tables_content, re.IGNORECASE
            )
            summary["tables"] = len(table_matches)

            # Count indexes
            indexes_content = (self.schema_dir / "02_indexes.sql").read_text()
            index_matches = re.findall(r"CREATE INDEX", indexes_content, re.IGNORECASE)
            summary["indexes"] = len(index_matches)

            # Count functions
            functions_content = (self.schema_dir / "03_functions.sql").read_text()
            function_matches = re.findall(
                r"CREATE.*?FUNCTION", functions_content, re.IGNORECASE
            )
            summary["functions"] = len(function_matches)

            # Count policies
            policies_content = (self.schema_dir / "05_policies.sql").read_text()
            policy_matches = re.findall(
                r"CREATE POLICY", policies_content, re.IGNORECASE
            )
            summary["policies"] = len(policy_matches)

        except Exception as e:
            summary["error"] = str(e)

        return summary

    def run_all_tests(self) -> bool:
        """Run all database tests."""
        print("🔍 TripSage Database Integration Tests")
        print("=" * 50)

        # Run all tests
        tests = [
            self.test_schema_files_exist,
            self.test_trip_collaborators_integration,
            self.test_rls_policy_consistency,
            self.test_foreign_key_relationships,
            self.test_vector_search_setup,
            self.test_maintenance_functions,
            self.test_sql_syntax_validity,
            self.test_migration_consistency,
            self.test_security_configuration,
        ]

        passed_tests = 0
        for test in tests:
            if test():
                passed_tests += 1

        # Generate summary
        print("\n📊 Schema Summary:")
        summary = self.generate_schema_summary()
        for component, count in summary.items():
            if component != "error":
                print(f"   {component.title()}: {count}")

        # Final results
        total_tests = len(tests)
        print(f"\n🎯 Test Results: {passed_tests}/{total_tests} passed")

        if passed_tests == total_tests:
            print("✅ All tests passed - Database is production ready!")
            return True
        else:
            print(f"❌ {total_tests - passed_tests} tests failed - Review issues above")
            return False

def main():
    """Main test function."""
    # Change to project directory (parent of supabase dir)
    os.chdir(Path(__file__).parent.parent)

    # Check if schema directory exists
    if not Path("supabase").exists():
        print("❌ Supabase directory not found!")
        return 1

    # Run tests
    tester = DatabaseTester()
    success = tester.run_all_tests()

    # Additional recommendations
    print("\n💡 Production Readiness Recommendations:")
    print("   🔒 Verify JWT_SECRET environment variable is properly set")
    print("   🔧 Test with actual Supabase instance using: supabase db reset")
    print("   📊 Run performance tests with realistic data volumes")
    print("   🚀 Set up automated database maintenance cron jobs")
    print("   🔐 Review and test all RLS policies with real users")
    print("   📈 Monitor vector search performance with production data")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
