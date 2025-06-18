#!/usr/bin/env python3
"""
Migration guide script for Enhanced Database Service.

This script provides guidance and tools for migrating from the original
DatabaseService to the enhanced version with LIFO pooling and monitoring.

Features:
- Compatibility check
- Configuration validation
- Performance comparison
- Migration assistance
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnhancedDatabaseServiceMigrator:
    """Helps migrate to the Enhanced Database Service."""

    def __init__(self, project_root: str = None):
        """Initialize migrator."""
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def analyze_current_usage(self) -> Dict[str, List[str]]:
        """Analyze current DatabaseService usage in the codebase."""
        logger.info("Analyzing current DatabaseService usage...")

        usage_patterns = {
            "direct_imports": [],
            "dependency_usage": [],
            "test_files": [],
            "configuration_files": [],
        }

        # Find Python files in the project
        py_files = list(self.project_root.rglob("*.py"))

        for file_path in py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                relative_path = str(file_path.relative_to(self.project_root))

                # Check for DatabaseService imports
                if (
                    "from tripsage_core.services.infrastructure.database_service import"
                    in content
                ):
                    usage_patterns["direct_imports"].append(relative_path)

                if "DatabaseService" in content and "test" in relative_path.lower():
                    usage_patterns["test_files"].append(relative_path)

                if "get_database_service" in content:
                    usage_patterns["dependency_usage"].append(relative_path)

                if any(
                    config_name in relative_path.lower()
                    for config_name in ["config", "settings", "dependencies"]
                ):
                    if "DatabaseService" in content:
                        usage_patterns["configuration_files"].append(relative_path)

            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")

        return usage_patterns

    def check_compatibility(self) -> Dict[str, bool]:
        """Check compatibility with enhanced database service."""
        logger.info("Checking compatibility...")

        compatibility = {
            "python_version": sys.version_info >= (3, 11),
            "prometheus_available": self._check_prometheus_availability(),
            "supabase_available": self._check_supabase_availability(),
            "config_compatible": self._check_config_compatibility(),
        }

        return compatibility

    def _check_prometheus_availability(self) -> bool:
        """Check if Prometheus client is available."""
        try:
            import prometheus_client

            return True
        except ImportError:
            return False

    def _check_supabase_availability(self) -> bool:
        """Check if Supabase client is available."""
        try:
            import supabase

            return True
        except ImportError:
            return False

    def _check_config_compatibility(self) -> bool:
        """Check if configuration is compatible."""
        try:
            from tripsage_core.config import get_settings

            settings = get_settings()

            # Check required settings
            required_attrs = [
                "database_url",
                "database_public_key",
            ]

            return all(hasattr(settings, attr) for attr in required_attrs)
        except Exception:
            return False

    def generate_migration_plan(self) -> Dict[str, List[str]]:
        """Generate step-by-step migration plan."""
        logger.info("Generating migration plan...")

        usage = self.analyze_current_usage()
        compatibility = self.check_compatibility()

        plan = {
            "prerequisites": [],
            "code_changes": [],
            "testing_steps": [],
            "monitoring_setup": [],
            "rollback_plan": [],
        }

        # Prerequisites
        if not compatibility["prometheus_available"]:
            plan["prerequisites"].append(
                "Install prometheus_client: pip install prometheus_client"
            )

        if not compatibility["python_version"]:
            plan["prerequisites"].append("Upgrade to Python 3.11 or higher")

        # Code changes
        for file_path in usage["direct_imports"]:
            plan["code_changes"].append(f"Update imports in {file_path}")

        for file_path in usage["dependency_usage"]:
            plan["code_changes"].append(f"Update dependency injection in {file_path}")

        # Testing steps
        plan["testing_steps"].extend(
            [
                "Run existing database tests to ensure compatibility",
                "Run performance benchmark script",
                "Validate connection pool behavior",
                "Test monitoring metrics collection",
                "Verify regression detection functionality",
            ]
        )

        # Monitoring setup
        plan["monitoring_setup"].extend(
            [
                "Configure Prometheus metrics collection",
                "Set up performance dashboards",
                "Configure regression detection alerts",
                "Test connection health monitoring",
            ]
        )

        # Rollback plan
        plan["rollback_plan"].extend(
            [
                "Keep backup of original DatabaseService imports",
                "Maintain original service configuration",
                "Document rollback procedure",
                "Test rollback in staging environment",
            ]
        )

        return plan

    def print_migration_report(self):
        """Print comprehensive migration report."""
        print("\n" + "=" * 80)
        print("ENHANCED DATABASE SERVICE MIGRATION REPORT")
        print("=" * 80)

        # Current usage analysis
        usage = self.analyze_current_usage()
        print("\nCURRENT USAGE ANALYSIS:")
        print("-" * 30)
        print(f"Direct imports found: {len(usage['direct_imports'])}")
        print(f"Dependency usage found: {len(usage['dependency_usage'])}")
        print(f"Test files affected: {len(usage['test_files'])}")
        print(f"Configuration files affected: {len(usage['configuration_files'])}")

        if usage["direct_imports"]:
            print("\nFiles with direct imports:")
            for file_path in usage["direct_imports"][:5]:  # Show first 5
                print(f"  - {file_path}")
            if len(usage["direct_imports"]) > 5:
                print(f"  ... and {len(usage['direct_imports']) - 5} more")

        # Compatibility check
        compatibility = self.check_compatibility()
        print("\nCOMPATIBILITY CHECK:")
        print("-" * 20)
        for check, status in compatibility.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {check.replace('_', ' ').title()}: {status}")

        # Migration plan
        plan = self.generate_migration_plan()
        print("\nMIGRATION PLAN:")
        print("-" * 15)

        if plan["prerequisites"]:
            print("\n📋 Prerequisites:")
            for step in plan["prerequisites"]:
                print(f"  • {step}")

        if plan["code_changes"]:
            print("\n🔧 Code Changes:")
            for change in plan["code_changes"][:10]:  # Show first 10
                print(f"  • {change}")
            if len(plan["code_changes"]) > 10:
                print(f"  • ... and {len(plan['code_changes']) - 10} more files")

        print("\n🧪 Testing Steps:")
        for step in plan["testing_steps"]:
            print(f"  • {step}")

        print("\n📊 Monitoring Setup:")
        for step in plan["monitoring_setup"]:
            print(f"  • {step}")

        print("\n🔄 Rollback Plan:")
        for step in plan["rollback_plan"]:
            print(f"  • {step}")

        # Benefits summary
        print("\nEXPECTED BENEFITS:")
        print("-" * 18)
        print("  ✨ LIFO connection pooling for better cache locality")
        print("  📊 Enhanced Prometheus metrics with percentiles")
        print("  🔍 Performance regression detection")
        print("  ❤️  Connection health monitoring")
        print("  🔧 Pre-ping connection validation")
        print("  🚀 Improved overall performance")

        # Recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 15)

        all_compatible = all(compatibility.values())
        if all_compatible:
            print("  🎉 Your project is ready for migration!")
            print("  📝 Follow the migration plan above")
            print("  🧪 Test thoroughly in staging environment")
            print("  📊 Set up monitoring before production deployment")
        else:
            print("  ⚠️  Address compatibility issues first")
            print("  🔧 Install missing dependencies")
            print("  📋 Review prerequisites carefully")

        print("\n" + "=" * 80)


def main():
    """Run the migration analysis."""
    print("Enhanced Database Service Migration Tool")
    print("=" * 50)

    # Get project root from command line or use current directory
    project_root = sys.argv[1] if len(sys.argv) > 1 else None

    migrator = EnhancedDatabaseServiceMigrator(project_root)
    migrator.print_migration_report()

    print("\nFor detailed migration assistance:")
    print("1. Review the Enhanced Database Service documentation")
    print("2. Run the performance benchmark script")
    print("3. Test in staging environment before production")
    print("4. Monitor performance metrics after deployment")


if __name__ == "__main__":
    main()
