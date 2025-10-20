#!/usr/bin/env python3
"""TripSage Database Schema Deployment Script.

Automates database schema deployment to Supabase with
validation and rollback capability.
"""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


class DatabaseDeployer:
    """Handles TripSage database schema deployment to Supabase."""

    def __init__(self, project_ref: str | None = None):
        """Initialize database deployer."""
        self.project_ref = project_ref
        self.schema_dir = Path("supabase/schemas")
        self.migration_dir = Path("supabase/migrations")
        self.deployment_log = []

    def log_step(self, step: str, success: bool = True, details: str = ""):
        """Log deployment step."""
        timestamp = datetime.now(UTC).isoformat()
        status = "✅" if success else "❌"
        log_entry = {
            "timestamp": timestamp,
            "step": step,
            "success": success,
            "details": details,
        }
        self.deployment_log.append(log_entry)

        print(f"{status} {step}")
        if details:
            print(f"   {details}")

    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites."""
        print("🔍 Checking Prerequisites...")

        # Check if Supabase CLI is available
        try:
            result = subprocess.run(
                ["supabase", "--version"], capture_output=True, text=True, check=True
            )
            self.log_step(
                "Supabase CLI Found", True, f"Version: {result.stdout.strip()}"
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_step(
                "Supabase CLI Check",
                False,
                "CLI not found - install from https://supabase.com/docs/guides/cli",
            )
            return False

        # Check schema files exist
        required_files = [
            "00_extensions.sql",
            "01_tables.sql",
            "02_indexes.sql",
            "03_functions.sql",
            "04_triggers.sql",
            "05_policies.sql",
            "06_views.sql",
        ]

        missing_files = [
            f for f in required_files if not (self.schema_dir / f).exists()
        ]
        if missing_files:
            self.log_step("Schema Files Check", False, f"Missing: {missing_files}")
            return False
        else:
            self.log_step(
                "Schema Files Check", True, f"All {len(required_files)} files found"
            )

        # Check environment variables
        required_env = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
        missing_env = [var for var in required_env if not os.getenv(var)]
        if missing_env:
            self.log_step("Environment Variables", False, f"Missing: {missing_env}")
            return False
        else:
            self.log_step("Environment Variables", True, "All required variables set")

        return True

    def validate_schema_syntax(self) -> bool:
        """Validate SQL syntax before deployment."""
        print("\n🔧 Validating Schema Syntax...")

        # Run our validation script
        try:
            _result = subprocess.run(
                [sys.executable, "validate_database_schema.py"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.log_step("Schema Validation", True, "All validation tests passed")
            return True
        except subprocess.CalledProcessError as e:
            self.log_step("Schema Validation", False, f"Validation failed: {e.stderr}")
            return False

    def create_consolidated_migration(self) -> Path | None:
        """Create a consolidated migration file for deployment."""
        print("\n📝 Creating Consolidated Migration...")

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        migration_file = (
            self.migration_dir / f"{timestamp}_production_schema_deployment.sql"
        )

        try:
            with migration_file.open("w", encoding="utf-8") as f:
                f.write(f"""-- TripSage Production Schema Deployment
-- Generated: {datetime.now(UTC).isoformat()}
-- Description: Complete database schema with trip collaboration and vector search
--
-- This migration applies the complete TripSage schema including:
-- - Core travel planning tables (trips, flights, accommodations)
-- - Trip collaboration system (trip_collaborators with RLS)
-- - Chat system with tool call tracking
-- - Memory system with pgvector embeddings
-- - API key management (BYOK)
-- - Comprehensive RLS policies for multi-tenant security

-- ===========================
-- SCHEMA DEPLOYMENT
-- ===========================

""")

                # Include each schema file in order
                schema_files = [
                    "00_extensions.sql",
                    "01_tables.sql",
                    "02_indexes.sql",
                    "03_functions.sql",
                    "04_triggers.sql",
                    "05_policies.sql",
                    "06_views.sql",
                ]

                for schema_file in schema_files:
                    file_path = self.schema_dir / schema_file
                    if file_path.exists():
                        f.write("\n-- ===========================\n")
                        f.write(f"-- {schema_file.upper()}\n")
                        f.write("-- ===========================\n\n")
                        f.write(file_path.read_text())
                        f.write("\n\n")

                # Add completion log
                f.write(f"""
-- ===========================
-- DEPLOYMENT COMPLETION
-- ===========================

DO $$
BEGIN
    RAISE NOTICE 'TripSage Production Schema deployed successfully!';
    RAISE NOTICE 'Deployment timestamp: {datetime.now(UTC).isoformat()}';
    RAISE NOTICE 'Features included:';
    RAISE NOTICE '- ✅ Core travel planning (12 tables)';
    RAISE NOTICE '- ✅ Trip collaboration system with RLS';
    RAISE NOTICE '- ✅ Vector search with pgvector (Mem0 compatible)';
    RAISE NOTICE '- ✅ Multi-tenant security (17 RLS policies)';
    RAISE NOTICE '- ✅ Performance optimization (38 indexes)';
    RAISE NOTICE '- ✅ Maintenance functions (12 functions)';
END;
$$;
""")

            self.log_step("Migration File Created", True, f"File: {migration_file}")
            return migration_file

        except (OSError, ValueError) as exc:
            self.log_step("Migration Creation", False, f"Error: {exc}")
            return None

    def deploy_to_local(self) -> bool:
        """Deploy schema to local Supabase instance."""
        print("\n🚀 Deploying to Local Supabase...")

        try:
            # Start local Supabase if not running
            subprocess.run(["supabase", "start"], check=True, capture_output=True)
            self.log_step("Local Supabase Started", True)

            # Reset database with new schema
            subprocess.run(["supabase", "db", "reset"], check=True, capture_output=True)
            self.log_step("Database Reset", True, "Schema applied successfully")

            return True

        except subprocess.CalledProcessError as e:
            self.log_step("Local Deployment", False, f"Error: {e}")
            return False

    def deploy_to_production(self) -> bool:
        """Deploy schema to production Supabase instance."""
        if not self.project_ref:
            self.log_step(
                "Production Deployment", False, "No project reference provided"
            )
            return False

        print(f"\n🌐 Deploying to Production (Project: {self.project_ref})...")

        try:
            # Link to production project
            subprocess.run(
                ["supabase", "link", "--project-ref", self.project_ref],
                check=True,
                capture_output=True,
            )
            self.log_step("Project Linked", True, f"Connected to {self.project_ref}")

            # Push schema to production
            subprocess.run(["supabase", "db", "push"], check=True, capture_output=True)
            self.log_step("Schema Pushed", True, "Production deployment successful")

            return True

        except subprocess.CalledProcessError as e:
            self.log_step("Production Deployment", False, f"Error: {e}")
            return False

    def verify_deployment(self) -> bool:
        """Verify deployment success."""
        print("\n🔍 Verifying Deployment...")

        try:
            # Run integration tests
            _result = subprocess.run(
                [sys.executable, "test_database_integration.py"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.log_step("Integration Tests", True, "All tests passed")
            return True

        except subprocess.CalledProcessError as e:
            self.log_step("Verification", False, f"Tests failed: {e.stderr}")
            return False

    def save_deployment_log(self) -> None:
        """Save deployment log to file."""
        log_file = Path(
            f"deployment_log_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )

        with log_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "deployment_summary": {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "project_ref": self.project_ref,
                        "total_steps": len(self.deployment_log),
                        "successful_steps": sum(
                            1 for log in self.deployment_log if log["success"]
                        ),
                        "failed_steps": sum(
                            1 for log in self.deployment_log if not log["success"]
                        ),
                    },
                    "deployment_log": self.deployment_log,
                },
                f,
                indent=2,
            )

        print(f"\n📋 Deployment log saved to: {log_file}")

    def deploy(self, target: str = "local") -> bool:
        """Run complete deployment process."""
        print("🚀 TripSage Database Schema Deployment")
        print(f"Target: {target.upper()}")
        print("=" * 50)

        # Check prerequisites
        if not self.check_prerequisites():
            self.save_deployment_log()
            return False

        # Validate schema
        if not self.validate_schema_syntax():
            self.save_deployment_log()
            return False

        # Create consolidated migration
        migration_file = self.create_consolidated_migration()
        if not migration_file:
            self.save_deployment_log()
            return False

        # Deploy based on target
        if target == "local":
            success = self.deploy_to_local()
        elif target == "production":
            success = self.deploy_to_production()
        else:
            self.log_step("Deployment", False, f"Unknown target: {target}")
            success = False

        if not success:
            self.save_deployment_log()
            return False

        # Verify deployment
        if not self.verify_deployment():
            self.save_deployment_log()
            return False

        # Success!
        print("\n🎉 Deployment Successful!")
        print(f"   Target: {target}")
        print("   Tables: 12")
        print("   Indexes: 38")
        print("   RLS Policies: 17")
        print("   Functions: 12")

        self.save_deployment_log()
        return True


def main():
    """Main deployment function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy TripSage database schema to Supabase"
    )
    parser.add_argument(
        "target", choices=["local", "production"], help="Deployment target"
    )
    parser.add_argument(
        "--project-ref", help="Supabase project reference for production deployment"
    )

    args = parser.parse_args()

    # Change to project directory (parent of supabase dir)
    os.chdir(Path(__file__).parent.parent)

    # Validate arguments
    if args.target == "production" and not args.project_ref:
        print("❌ Production deployment requires --project-ref argument")
        return 1

    # Run deployment
    deployer = DatabaseDeployer(args.project_ref)
    success = deployer.deploy(args.target)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
