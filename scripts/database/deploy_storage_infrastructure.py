#!/usr/bin/env python3
"""TripSage Storage Infrastructure Deployment Script.

Description: Deploys complete file storage infrastructure to Supabase
Created: 2025-01-11
Version: 1.0.
"""

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Any, cast

import supabase


class StorageDeployment:
    """Handles deployment of storage infrastructure to Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, db_url: str):
        """Initialize storage deployment with Supabase credentials."""
        # Avoid tight typing on third-party; use runtime factory
        self.supabase: Any = supabase.create_client(  # type: ignore[attr-defined]  # pylint: disable=no-member,c-extension-no-member
            supabase_url, supabase_key
        )
        self.db_url = db_url
        self.project_root = Path(__file__).parent.parent.parent
        self.storage_dir = self.project_root / "supabase" / "storage"

    async def deploy_all(self) -> dict[str, bool]:
        """Deploy complete storage infrastructure."""
        results: dict[str, bool] = {}

        print("Starting TripSage Storage Infrastructure Deployment...")
        print("=" * 60)

        try:
            # 1. Run storage migration
            print("\nStep 1: Running storage migration...")
            results["migration"] = await self.run_storage_migration()

            # 2. Verify buckets
            print("\nStep 2: Verifying storage buckets...")
            results["buckets"] = await self.verify_buckets()

            # 3. Test RLS policies
            print("\nStep 3: Testing RLS policies...")
            results["policies"] = await self.test_rls_policies()

            # 4. Legacy Edge Function check (now retired)
            print("\nStep 4: Confirming Edge Function retirement...")
            results["edge_function"] = await self.deploy_edge_function()

            # 5. Configure webhooks
            print("\nStep 5: Configuring webhooks...")
            results["webhooks"] = await self.configure_webhooks()

            # 6. Run verification tests
            print("\nStep 6: Running verification tests...")
            results["verification"] = await self.run_verification_tests()

            # Print summary
            self.print_deployment_summary(results)

            return results

        except Exception as e:  # noqa: BLE001
            print(f"Deployment failed: {e}")
            return {"deployment": False}

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

            module: Any = importlib.import_module("asyncpg")
            connect_func: Any = module.connect
            conn: Any = await connect_func(self.db_url)

            try:
                # Read migration file
                migration_sql = migration_file.read_text()

                # Execute migration
                await conn.execute(migration_sql)
                print("Storage migration completed successfully")
                return True

            finally:
                await conn.close()

        except Exception as e:  # noqa: BLE001
            print(f"Migration failed: {e}")
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
                print(f"Missing buckets: {missing_buckets}")
                return False

            print(f"All buckets verified: {existing_buckets}")
            return True

        except Exception as e:  # noqa: BLE001
            print(f"Bucket verification failed: {e}")
            return False

    async def test_rls_policies(self) -> bool:
        """Test RLS policies are working correctly."""
        try:
            module: Any = importlib.import_module("asyncpg")
            connect_func: Any = module.connect
            conn: Any = await connect_func(self.db_url)

            try:
                # Test query to check if policies exist
                policy_count: int | None = cast(
                    int | None,
                    await conn.fetchval(
                        """
                    SELECT COUNT(*)
                    FROM pg_policies
                    WHERE schemaname = 'storage'
                    AND tablename = 'objects'
                    AND policyname LIKE '%attachments%'
                """
                    ),
                )

                if (policy_count or 0) == 0:
                    print("No storage policies found")
                    return False

                print(f"Found {policy_count} storage policies")
                return True

            finally:
                await conn.close()

        except Exception as e:  # noqa: BLE001
            print(f"RLS policy test failed: {e}")
            return False

    async def deploy_edge_function(self) -> bool:
        """No-op: Edge Functions retired. Webhooks use DB → Vercel.

        Kept for backward compatibility of scripts; always returns True.
        """
        print(
            "Edge Functions retired — using Database Webhooks → Vercel. Skipping deploy."  # noqa: E501
        )
        return True

    async def configure_webhooks(self) -> bool:
        """Validate consolidated DB→Vercel webhook functions exist."""
        try:
            module: Any = importlib.import_module("asyncpg")
            connect_func: Any = module.connect
            conn: Any = await connect_func(self.db_url)

            try:
                # Check consolidated webhook functions exist
                trips_fn = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc p
                        JOIN pg_namespace n ON p.pronamespace = n.oid
                        WHERE n.nspname = 'public'
                          AND p.proname = 'notify_trip_collaborators_http'
                    )
                    """
                )
                cache_fn = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc p
                        JOIN pg_namespace n ON p.pronamespace = n.oid
                        WHERE n.nspname = 'public'
                          AND p.proname = 'notify_table_change_cache_http'
                    )
                    """
                )

                if not trips_fn or not cache_fn:
                    print("Consolidated webhook functions not found. Apply migrations.")
                    return False

                # Check a sample trigger exists
                trigger_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_trigger t
                        JOIN pg_class c ON t.tgrelid = c.oid
                        JOIN pg_namespace n ON c.relnamespace = n.oid
                        WHERE n.nspname = 'public' AND t.tgname = 'trg_trips_cache_webhook'
                    )
                    """  # noqa: E501
                )

                if not trigger_exists:
                    print("Cache webhook trigger not found. Apply migrations.")
                    return False

                print("Webhooks configured and verified")
                return True

            finally:
                await conn.close()

        except Exception as e:  # noqa: BLE001
            print(f"Webhook configuration failed: {e}")
            return False

    async def run_verification_tests(self) -> bool:
        """Run verification tests for storage infrastructure."""
        try:
            module: Any = importlib.import_module("asyncpg")
            connect_func: Any = module.connect
            conn: Any = await connect_func(self.db_url)

            try:
                # Test storage functions
                functions_to_test = [
                    "cleanup_orphaned_files",
                    "get_user_storage_usage",
                    "check_storage_quota",
                    "validate_file_upload",
                ]

                for func_name in functions_to_test:
                    func_exists: bool | None = cast(
                        bool | None,
                        await conn.fetchval(
                            """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_proc p
                            JOIN pg_namespace n ON p.pronamespace = n.oid
                            WHERE n.nspname = 'public'
                            AND p.proname = $1
                        )
                        """,
                            func_name,
                        ),
                    )

                    if not func_exists:
                        print(f"Function {func_name} not found")
                        return False

                # Test storage tables
                tables_to_test = [
                    "file_attachments",
                    "file_processing_queue",
                    "file_versions",
                ]

                for table_name in tables_to_test:
                    table_exists: bool | None = cast(
                        bool | None,
                        await conn.fetchval(
                            """
                        SELECT EXISTS (
                            SELECT 1 FROM pg_tables
                            WHERE schemaname = 'public'
                            AND tablename = $1
                        )
                        """,
                            table_name,
                        ),
                    )

                    if not table_exists:
                        print(f"Table {table_name} not found")
                        return False

                print("All verification tests passed")
                return True

            finally:
                await conn.close()

        except Exception as e:  # noqa: BLE001
            print(f"Verification tests failed: {e}")
            return False

    def print_deployment_summary(self, results: dict[str, bool]) -> None:
        """Print deployment summary."""
        print("\n" + "=" * 60)
        print("DEPLOYMENT SUMMARY")
        print("=" * 60)

        total_steps = len(results)
        successful_steps = sum(1 for success in results.values() if success)

        for step, success in results.items():
            status = "OK" if success else "FAIL"
            print(f"[{status}] {step.replace('_', ' ').title()}")

        success_rate = (successful_steps / total_steps) * 100
        print(f"\nSuccess Rate: {successful_steps}/{total_steps} ({success_rate:.1f}%)")

        if successful_steps == total_steps:
            print("\nStorage infrastructure deployment completed successfully")
            print("\nNext Steps:")
            print("1. Configure DB→Vercel webhooks: scripts/operators/setup_webhooks.sh")
            print("2. Verify HMAC secret alignment: scripts/operators/verify_webhook_secret.sh")
            print("3. Configure Vercel env vars (HMAC_SECRET, Upstash, QStash, Resend)")
            print("4. Set up CORS settings for browser uploads")
            print("5. Test file upload/download + webhook delivery flows")
            print(
                "6. Monitor storage usage plus [operational-alert] logs for "
                "redis.unavailable + webhook.verification_failed events"
            )
        else:
            print(
                "\nSome deployment steps failed. "
                "Please review and fix issues before proceeding."
            )


async def main():
    """Main deployment function."""
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not all([supabase_url, supabase_key, db_url]):
        print("Missing required environment variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_ROLE_KEY")
        print("   - DATABASE_URL")
        sys.exit(1)

    # Narrow Optional[str] types for static checkers
    assert supabase_url is not None
    assert supabase_key is not None
    assert db_url is not None

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
