#!/usr/bin/env python3
"""Helper script to test and validate migrated database connections with secure utilities.

This script validates all database connection methods after migration to ensure
they're using the secure URL parsing and validation utilities correctly.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from tripsage_core.config import get_settings
from tripsage_core.database.connection import (
    create_secure_async_engine,
    get_database_session,
)
from tripsage_core.utils.connection_utils import (
    DatabaseConnectionError,
    DatabaseURLParsingError,
    SecureDatabaseConnectionManager,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ConnectionMigrationTester:
    """Test all database connections after migration to secure utilities."""

    def __init__(self):
        self.settings = get_settings()
        self.manager = SecureDatabaseConnectionManager()
        self.converter = DatabaseURLConverter()
        self.results: dict[str, dict] = {}
        self.start_time = datetime.utcnow()

    async def test_supabase_api_connection(self) -> bool:
        """Test Supabase API connection using client library."""
        test_name = "supabase_api"
        logger.info(f"Testing {test_name} connection...")

        try:
            from supabase import create_client

            client = create_client(
                self.settings.database_url,
                self.settings.database_public_key.get_secret_value(),
            )

            # Simple test query
            _ = client.table("users").select("id").limit(1).execute()

            self.results[test_name] = {
                "success": True,
                "message": "Supabase API connection successful",
                "duration_ms": self._get_duration_ms(),
            }
            logger.info(f"✅ {test_name} connection successful")
            return True

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} connection failed: {e}")
            return False

    async def test_postgres_direct_connection(self) -> bool:
        """Test direct PostgreSQL connection with secure URL conversion."""
        test_name = "postgres_direct"
        logger.info(f"Testing {test_name} connection...")

        try:
            # Convert Supabase URL to PostgreSQL
            postgres_url = self.converter.supabase_to_postgres(
                self.settings.database_url,
                self.settings.database_service_key.get_secret_value(),
                use_pooler=False,
            )

            # Validate URL security
            credentials = await self.manager.parse_and_validate_url(postgres_url)

            # Test actual connection
            engine = await create_secure_async_engine(
                postgres_url,
                pool_size=2,
                max_overflow=0,
            )

            try:
                from sqlalchemy import text

                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT version()"))
                    version = result.scalar()

                    # Check for pgvector extension
                    ext_result = await conn.execute(
                        text(
                            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
                        )
                    )
                    has_vector = ext_result.scalar() is not None

                self.results[test_name] = {
                    "success": True,
                    "message": "Direct PostgreSQL connection successful",
                    "postgres_version": version,
                    "has_pgvector": has_vector,
                    "hostname": credentials.hostname,
                    "database": credentials.database,
                    "duration_ms": self._get_duration_ms(),
                }
                logger.info(f"✅ {test_name} connection successful")
                return True

            finally:
                await engine.dispose()

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} connection failed: {e}")
            return False

    async def test_postgres_pooler_connection(self) -> bool:
        """Test PostgreSQL connection via pooler."""
        test_name = "postgres_pooler"
        logger.info(f"Testing {test_name} connection...")

        try:
            # Convert to pooler URL
            pooler_url = self.converter.supabase_to_postgres(
                self.settings.database_url,
                self.settings.database_service_key.get_secret_value(),
                use_pooler=True,
            )

            # Validate URL
            credentials = await self.manager.parse_and_validate_url(pooler_url)

            # Test connection
            engine = await create_secure_async_engine(
                pooler_url,
                pool_size=2,
                max_overflow=0,
            )

            try:
                from sqlalchemy import text

                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    _ = result.scalar()

                self.results[test_name] = {
                    "success": True,
                    "message": "Pooler PostgreSQL connection successful",
                    "port": credentials.port,
                    "hostname": credentials.hostname,
                    "duration_ms": self._get_duration_ms(),
                }
                logger.info(f"✅ {test_name} connection successful")
                return True

            finally:
                await engine.dispose()

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} connection failed: {e}")
            return False

    async def test_memory_service_connection(self) -> bool:
        """Test memory service connection using migrated utilities."""
        test_name = "memory_service"
        logger.info(f"Testing {test_name} connection...")

        try:
            # Test via the standard database session
            async with get_database_session() as session:
                from sqlalchemy import text

                # Check if memory-related tables exist
                result = await session.execute(
                    text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name LIKE '%memory%'
                        LIMIT 5
                    """)
                )

                memory_tables = [row[0] for row in result]

            self.results[test_name] = {
                "success": True,
                "message": "Memory service connection successful",
                "memory_tables_found": len(memory_tables),
                "tables": memory_tables,
                "duration_ms": self._get_duration_ms(),
            }
            logger.info(f"✅ {test_name} connection successful")
            return True

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} connection failed: {e}")
            return False

    async def test_checkpoint_manager_connection(self) -> bool:
        """Test checkpoint manager connection after migration."""
        test_name = "checkpoint_manager"
        logger.info(f"Testing {test_name} connection...")

        try:
            from tripsage.orchestration.checkpoint_manager import (
                POSTGRES_AVAILABLE,
                SupabaseCheckpointManager,
            )

            if not POSTGRES_AVAILABLE:
                self.results[test_name] = {
                    "success": False,
                    "error": "PostgreSQL checkpoint dependencies not available",
                    "duration_ms": self._get_duration_ms(),
                }
                logger.warning(f"⚠️  {test_name} skipped - dependencies not available")
                return False

            manager = SupabaseCheckpointManager()

            # Test connection string building
            conn_string = manager._build_connection_string()

            # Verify it's a valid PostgreSQL URL
            if not conn_string.startswith("postgresql://"):
                raise ValueError(
                    f"Invalid connection string format: {conn_string[:20]}..."
                )

            # Test async checkpointer initialization
            _ = await manager.get_async_checkpointer()

            # Get checkpoint stats
            stats = await manager.get_checkpoint_stats()

            self.results[test_name] = {
                "success": True,
                "message": "Checkpoint manager connection successful",
                "has_secure_url": "sslmode=require" in conn_string,
                "checkpoint_stats": stats,
                "duration_ms": self._get_duration_ms(),
            }
            logger.info(f"✅ {test_name} connection successful")

            # Cleanup
            await manager.close()
            return True

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} connection failed: {e}")
            return False

    async def test_connection_security_features(self) -> bool:
        """Test security features of the connection utilities."""
        test_name = "security_features"
        logger.info(f"Testing {test_name}...")

        security_checks = {
            "url_validation": False,
            "credential_masking": False,
            "circuit_breaker": False,
            "retry_logic": False,
            "ssl_required": False,
        }

        try:
            # Test URL validation
            try:
                await self.manager.parse_and_validate_url("invalid://url")
            except DatabaseURLParsingError:
                security_checks["url_validation"] = True

            # Test credential masking
            postgres_url = self.converter.supabase_to_postgres(
                self.settings.database_url,
                "test_password_12345",
            )
            credentials = self.manager.url_parser.parse_url(postgres_url)
            masked = credentials.sanitized_for_logging()
            if "test_password_12345" not in masked and "***MASKED***" in masked:
                security_checks["credential_masking"] = True

            # Test circuit breaker (simulate failures)
            cb = self.manager.circuit_breaker
            original_threshold = cb.failure_threshold
            cb.failure_threshold = 2  # Lower threshold for testing

            async def failing_operation():
                raise DatabaseConnectionError("Test failure")

            # Trigger failures
            for _ in range(3):
                try:
                    await cb.call(failing_operation)
                except Exception:
                    pass

            # Circuit should be open now
            try:
                await cb.call(failing_operation)
            except DatabaseConnectionError as e:
                if "Circuit breaker is OPEN" in str(e):
                    security_checks["circuit_breaker"] = True

            cb.failure_threshold = original_threshold  # Reset

            # Test retry logic
            retry_handler = self.manager.retry_handler
            attempt_count = 0

            async def counting_operation():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise DatabaseConnectionError("Retry test")
                return True

            result = await retry_handler.execute_with_retry(counting_operation)
            if result and attempt_count == 2:
                security_checks["retry_logic"] = True

            # Test SSL requirement
            postgres_url = self.converter.supabase_to_postgres(
                self.settings.database_url,
                self.settings.database_service_key.get_secret_value(),
            )
            if "sslmode=require" in postgres_url:
                security_checks["ssl_required"] = True

            # Calculate success
            passed = sum(security_checks.values())
            total = len(security_checks)

            self.results[test_name] = {
                "success": passed == total,
                "message": f"Security features test: {passed}/{total} passed",
                "checks": security_checks,
                "duration_ms": self._get_duration_ms(),
            }

            if passed == total:
                logger.info(f"✅ {test_name} all checks passed")
            else:
                logger.warning(f"⚠️  {test_name} {passed}/{total} checks passed")

            return passed == total

        except Exception as e:
            self.results[test_name] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": self._get_duration_ms(),
            }
            logger.exception(f"❌ {test_name} failed: {e}")
            return False

    def _get_duration_ms(self) -> float:
        """Get duration since start in milliseconds."""
        duration = datetime.utcnow() - self.start_time
        return duration.total_seconds() * 1000

    async def run_all_tests(self) -> bool:
        """Run all connection tests and generate report."""
        logger.info("Starting database connection migration tests...")
        logger.info("=" * 60)

        # Run all tests
        test_methods = [
            self.test_supabase_api_connection,
            self.test_postgres_direct_connection,
            self.test_postgres_pooler_connection,
            self.test_memory_service_connection,
            self.test_checkpoint_manager_connection,
            self.test_connection_security_features,
        ]

        # Execute tests
        results = await asyncio.gather(
            *[test() for test in test_methods],
            return_exceptions=True,
        )

        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                test_name = test_methods[i].__name__.replace("test_", "")
                self.results[test_name] = {
                    "success": False,
                    "error": str(result),
                    "error_type": type(result).__name__,
                }

        # Generate summary
        self._print_summary()

        # Return overall success
        success_count = sum(1 for r in self.results.values() if r.get("success", False))
        return success_count == len(self.results)

    def _print_summary(self):
        """Print test results summary."""
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION TEST RESULTS")
        logger.info("=" * 60)

        # Summary stats
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get("success", False))
        failed = total - passed

        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed} ✅")
        logger.info(f"Failed: {failed} ❌")
        logger.info(f"Success Rate: {(passed / total) * 100:.1f}%")
        logger.info("-" * 60)

        # Detailed results
        for test_name, result in self.results.items():
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            duration = result.get("duration_ms", 0)
            logger.info(f"\n{test_name}: {status} ({duration:.1f}ms)")

            if result.get("success"):
                # Show success details
                for key, value in result.items():
                    if key not in ["success", "duration_ms", "message"]:
                        logger.info(f"  {key}: {value}")
            else:
                # Show error details
                logger.exception(f"  Error: {result.get('error', 'Unknown error')}")
                logger.exception(f"  Type: {result.get('error_type', 'Unknown')}")

        logger.info("\n" + "=" * 60)

        # Recommendations
        if failed > 0:
            logger.warning("\n⚠️  RECOMMENDATIONS:")
            logger.warning("1. Check database credentials and connectivity")
            logger.warning("2. Ensure all required extensions are installed")
            logger.warning("3. Verify SSL certificates are properly configured")
            logger.warning("4. Review error messages above for specific issues")
        else:
            logger.info("\n✅ All database connections successfully migrated!")
            logger.info("The secure connection utilities are working correctly.")


async def main():
    """Main entry point for migration testing."""
    tester = ConnectionMigrationTester()
    success = await tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
