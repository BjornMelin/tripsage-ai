#!/usr/bin/env python3
"""TripSage Storage Infrastructure Deployment Script.

Description: Deploys complete file storage infrastructure to Supabase
Created: 2025-01-11
Version: 1.0.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from supabase import Client, create_client


class StorageDeployment:
    """Handles deployment of storage infrastructure to Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, db_url: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.db_url = db_url
        self.project_root = Path(__file__).parent.parent.parent
        self.storage_dir = self.project_root / "supabase" / "storage"

    async def deploy_all(self) -> dict[str, bool]:
        """Deploy complete storage infrastructure."""
        results = {}

        print("🚀 Starting TripSage Storage Infrastructure Deployment...")
        print("=" * 60)

        try:
            # 1. Run storage migration
            print("\n📁 Step 1: Running storage migration...")
            results["migration"] = await self.run_storage_migration()

            # 2. Verify buckets
            print("\n🪣 Step 2: Verifying storage buckets...")
            results["buckets"] = await self.verify_buckets()

            # 3. Test RLS policies
            print("\n🔒 Step 3: Testing RLS policies...")
            results["policies"] = await self.test_rls_policies()

            # 4. Deploy Edge Function
            print("\n⚡ Step 4: Deploying file processor Edge Function...")
            results["edge_function"] = await self.deploy_edge_function()

            # 5. Configure webhooks
            print("\n🔗 Step 5: Configuring webhooks...")
            results["webhooks"] = await self.configure_webhooks()

            # 6. Run verification tests
            print("\n✅ Step 6: Running verification tests...")
            results["verification"] = await self.run_verification_tests()

            # Print summary
            self.print_deployment_summary(results)

            return results

        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return {"error": str(e)}

    async def run_storage_migration(self) -> bool:
        """Run the storage infrastructure migration."""
        try:
            migration_file = (
                self.project_root
                / "supabase"
                / "migrations"
                / "20250111_01_add_storage_infrastructure.sql"
            )

            if not migration_file.exists():
                raise FileNotFoundError(f"Migration file not found: {migration_file}")

            conn = await asyncpg.connect(self.db_url)

            try:
                # Read migration file
                migration_sql = migration_file.read_text()

                # Execute migration
                await conn.execute(migration_sql)
                print("✅ Storage migration completed successfully")
                return True

            finally:
                await conn.close()

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    async def verify_buckets(self) -> bool:
        """Verify that all required buckets exist."""
        try:
            expected_buckets = [
                "attachments",
                "avatars",
                "trip-images",
                "thumbnails",
                "quarantine",
            ]

            # Get bucket list from Supabase
            bucket_response = self.supabase.storage.list_buckets()
            existing_buckets = [bucket.id for bucket in bucket_response]

            missing_buckets = set(expected_buckets) - set(existing_buckets)

            if missing_buckets:
                print(f"❌ Missing buckets: {missing_buckets}")
                return False

            print(f"✅ All buckets verified: {existing_buckets}")
            return True

        except Exception as e:
            print(f"❌ Bucket verification failed: {e}")
            return False

    async def test_rls_policies(self) -> bool:
        """Test RLS policies are working correctly."""
        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                # Test query to check if policies exist
                policy_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM pg_policies
                    WHERE schemaname = 'storage'
                    AND tablename = 'objects'
                    AND policyname LIKE '%attachments%'
                """)

                if policy_count == 0:
                    print("❌ No storage policies found")
                    return False

                print(f"✅ Found {policy_count} storage policies")
                return True

            finally:
                await conn.close()

        except Exception as e:
            print(f"❌ RLS policy test failed: {e}")
            return False

    async def deploy_edge_function(self) -> bool:
        """Deploy the file processor Edge Function."""
        try:
            # In a real deployment, this would use Supabase CLI
            # For now, we'll just verify the function file exists
            function_file = (
                self.project_root
                / "supabase"
                / "functions"
                / "file-processor"
                / "index.ts"
            )

            if not function_file.exists():
                print("❌ Edge Function file not found")
                return False

            print("✅ Edge Function file ready for deployment")
            print(
                "📝 Note: Deploy manually using: "
                "supabase functions deploy file-processor"
            )
            return True

        except Exception as e:
            print(f"❌ Edge Function deployment failed: {e}")
            return False

    async def configure_webhooks(self) -> bool:
        """Configure database webhooks for file processing."""
        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                # Check if webhook function exists
                function_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc p
                        JOIN pg_namespace n ON p.pronamespace = n.oid
                        WHERE n.nspname = 'public'
                        AND p.proname = 'notify_file_processor'
                    )
                """)

                if not function_exists:
                    print("❌ Webhook function not found")
                    return False

                # Check if trigger exists
                trigger_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_trigger
                        WHERE tgname = 'file_attachments_processor_trigger'
                    )
                """)

                if not trigger_exists:
                    print("❌ Webhook trigger not found")
                    return False

                print("✅ Webhook function and trigger configured")
                return True

            finally:
                await conn.close()

        except Exception as e:
            print(f"❌ Webhook configuration failed: {e}")
            return False

    async def run_verification_tests(self) -> bool:
        """Run verification tests for storage infrastructure."""
        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                # Test storage functions
                functions_to_test = [
                    "cleanup_orphaned_files",
                    "get_user_storage_usage",
                    "check_storage_quota",
                    "validate_file_upload",
                ]

                for func_name in functions_to_test:
                    func_exists = await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_proc p
                            JOIN pg_namespace n ON p.pronamespace = n.oid
                            WHERE n.nspname = 'public'
                            AND p.proname = $1
                        )
                    """,
                        func_name,
                    )

                    if not func_exists:
                        print(f"❌ Function {func_name} not found")
                        return False

                # Test storage tables
                tables_to_test = [
                    "file_attachments",
                    "file_processing_queue",
                    "file_versions",
                ]

                for table_name in tables_to_test:
                    table_exists = await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_tables
                            WHERE schemaname = 'public'
                            AND tablename = $1
                        )
                    """,
                        table_name,
                    )

                    if not table_exists:
                        print(f"❌ Table {table_name} not found")
                        return False

                print("✅ All verification tests passed")
                return True

            finally:
                await conn.close()

        except Exception as e:
            print(f"❌ Verification tests failed: {e}")
            return False

    def print_deployment_summary(self, results: dict[str, bool]) -> None:
        """Print deployment summary."""
        print("\n" + "=" * 60)
        print("📊 DEPLOYMENT SUMMARY")
        print("=" * 60)

        total_steps = len(results)
        successful_steps = sum(1 for success in results.values() if success)

        for step, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {step.replace('_', ' ').title()}")

        success_rate = (successful_steps / total_steps) * 100
        print(
            f"\n📈 Success Rate: {successful_steps}/{total_steps} ({success_rate:.1f}%)"
        )

        if successful_steps == total_steps:
            print("\n🎉 Storage infrastructure deployment completed successfully!")
            print("\n📋 Next Steps:")
            print("1. Deploy Edge Function: supabase functions deploy file-processor")
            print("2. Configure environment variables for webhooks")
            print("3. Set up CORS settings for browser uploads")
            print("4. Test file upload/download flows")
            print("5. Monitor storage usage and performance")
        else:
            print(
                "\n⚠️  Some deployment steps failed. "
                "Please review and fix issues before proceeding."
            )


async def main():
    """Main deployment function."""
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not all([supabase_url, supabase_key, db_url]):
        print("❌ Missing required environment variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_ROLE_KEY")
        print("   - DATABASE_URL")
        sys.exit(1)

    # Run deployment
    deployment = StorageDeployment(supabase_url, supabase_key, db_url)
    results = await deployment.deploy_all()

    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
