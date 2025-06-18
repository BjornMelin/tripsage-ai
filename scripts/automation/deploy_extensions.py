#!/usr/bin/env python3
"""
Deploy Supabase Extensions and Automation
Applies all extension configurations and sets up automation features.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from rich.console import Console
from rich.panel import Panel

console = Console()

class ExtensionDeployer:
    def __init__(self, database_url: str, schema_path: Path):
        self.database_url = database_url
        self.schema_path = schema_path
        self.connection = None

    async def connect(self):
        """Connect to database."""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            console.print("✅ Connected to database", style="green")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
            sys.exit(1)

    async def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            await self.connection.close()

    async def execute_sql_file(self, file_path: Path, description: str = None) -> bool:
        """Execute SQL file."""
        try:
            with open(file_path, "r") as f:
                sql_content = f.read()

            console.print(f"📝 Executing: {description or file_path.name}")

            # Split on semicolon but be careful with function definitions
            statements = self._split_sql_statements(sql_content)

            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        await self.connection.execute(statement)
                    except Exception as e:
                        console.print(
                            f"⚠️  Warning in statement {i + 1}: {e}", style="yellow"
                        )
                        # Continue with other statements

            console.print(
                f"✅ Completed: {description or file_path.name}", style="green"
            )
            return True

        except Exception as e:
            console.print(f"❌ Failed to execute {file_path}: {e}", style="red")
            return False

    def _split_sql_statements(self, sql_content: str) -> list[str]:
        """Split SQL content into individual statements."""
        # This is a simple implementation - for production use a proper SQL parser
        statements = []
        current_statement = ""
        in_function = False

        lines = sql_content.split("\n")
        for line in lines:
            stripped = line.strip()

            # Skip comments
            if stripped.startswith("--") or not stripped:
                continue

            # Track if we're in a function definition
            if (
                "CREATE OR REPLACE FUNCTION" in line.upper()
                or "CREATE FUNCTION" in line.upper()
            ):
                in_function = True
            elif stripped.upper() == "END;" and in_function:
                in_function = False
                current_statement += line + "\n"
                statements.append(current_statement.strip())
                current_statement = ""
                continue

            current_statement += line + "\n"

            # If not in function and line ends with semicolon, it's a statement end
            if not in_function and stripped.endswith(";"):
                statements.append(current_statement.strip())
                current_statement = ""

        # Add any remaining content
        if current_statement.strip():
            statements.append(current_statement.strip())

        return statements

    async def deploy_extensions(self) -> bool:
        """Deploy core extensions."""
        console.print("\n🔧 Deploying Extensions...", style="bold blue")

        extensions_file = self.schema_path / "00_extensions.sql"
        if not extensions_file.exists():
            console.print(
                f"❌ Extensions file not found: {extensions_file}", style="red"
            )
            return False

        return await self.execute_sql_file(
            extensions_file, "Core Extensions and Realtime"
        )

    async def deploy_automation(self) -> bool:
        """Deploy automation functions and jobs."""
        console.print("\n⚙️ Deploying Automation...", style="bold blue")

        automation_file = self.schema_path / "07_automation.sql"
        if not automation_file.exists():
            console.print(
                f"❌ Automation file not found: {automation_file}", style="red"
            )
            return False

        return await self.execute_sql_file(
            automation_file, "Scheduled Jobs and Maintenance"
        )

    async def deploy_webhooks(self) -> bool:
        """Deploy webhook functions."""
        console.print("\n🔗 Deploying Webhook Integration...", style="bold blue")

        webhooks_file = self.schema_path / "08_webhooks.sql"
        if not webhooks_file.exists():
            console.print(f"❌ Webhooks file not found: {webhooks_file}", style="red")
            return False

        return await self.execute_sql_file(
            webhooks_file, "Webhook Functions and Triggers"
        )

    async def run_migration(self) -> bool:
        """Run the migration file."""
        console.print("\n📦 Running Migration...", style="bold blue")

        migration_file = (
            Path(__file__).parent.parent.parent
            / "supabase"
            / "migrations"
            / "20250611_02_enable_automation_extensions.sql"
        )
        if not migration_file.exists():
            console.print(f"❌ Migration file not found: {migration_file}", style="red")
            return False

        return await self.execute_sql_file(
            migration_file, "Automation Extensions Migration"
        )

    async def verify_deployment(self) -> dict[str, bool]:
        """Verify the deployment was successful."""
        console.print("\n🔍 Verifying Deployment...", style="bold blue")

        checks = {}

        # Check extensions
        try:
            extensions_query = """
            SELECT extname FROM pg_extension 
            WHERE extname IN ('pg_cron', 'pg_net', 'vector', 'uuid-ossp', 'pgcrypto')
            """
            extensions = await self.connection.fetch(extensions_query)
            checks["extensions"] = len(extensions) >= 5
            console.print(f"Extensions installed: {len(extensions)}/5")
        except Exception as e:
            checks["extensions"] = False
            console.print(f"❌ Extension check failed: {e}", style="red")

        # Check automation tables
        try:
            tables_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_name IN (
                'notifications', 'system_metrics', 'webhook_configs', 'webhook_logs'
            )
            """
            tables = await self.connection.fetch(tables_query)
            checks["automation_tables"] = len(tables) >= 4
            console.print(f"Automation tables created: {len(tables)}/4")
        except Exception as e:
            checks["automation_tables"] = False
            console.print(f"❌ Automation tables check failed: {e}", style="red")

        # Check realtime publication
        try:
            realtime_query = """
            SELECT COUNT(*) as table_count FROM pg_publication_tables 
            WHERE pubname = 'supabase_realtime'
            """
            result = await self.connection.fetchval(realtime_query)
            checks["realtime"] = result >= 6
            console.print(f"Realtime tables configured: {result}/6")
        except Exception as e:
            checks["realtime"] = False
            console.print(f"❌ Realtime check failed: {e}", style="red")

        # Check functions
        try:
            functions_query = """
            SELECT COUNT(*) FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' 
            AND p.proname IN (
                'verify_extensions', 'send_webhook_with_retry', 'list_scheduled_jobs'
            )
            """
            result = await self.connection.fetchval(functions_query)
            checks["functions"] = result >= 3
            console.print(f"Key functions created: {result}/3")
        except Exception as e:
            checks["functions"] = False
            console.print(f"❌ Functions check failed: {e}", style="red")

        return checks

    async def configure_default_webhooks(self) -> bool:
        """Configure default webhook endpoints."""
        console.print("\n🌐 Configuring Default Webhooks...", style="bold blue")

        try:
            # Update webhook URLs to use actual Supabase project URL if available
            supabase_url = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")

            update_query = """
            UPDATE webhook_configs 
            SET url = REPLACE(url, 'https://your-domain.supabase.co', $1)
            WHERE url LIKE '%your-domain.supabase.co%'
            """

            await self.connection.execute(update_query, supabase_url)
            console.print(f"✅ Updated webhook URLs to use: {supabase_url}")
            return True

        except Exception as e:
            console.print(
                f"⚠️  Warning: Could not update webhook URLs: {e}", style="yellow"
            )
            return False

    async def full_deployment(self):
        """Run complete deployment process."""
        console.print(
            Panel.fit(
                "[bold blue]TripSage Extensions & Automation Deployment[/bold blue]\n"
                "This will configure pg_cron, pg_net, realtime, "
                "and webhook integration.",
                title="🚀 Deployment Script",
            )
        )

        await self.connect()

        steps = [
            ("Deploy Extensions", self.deploy_extensions()),
            ("Run Migration", self.run_migration()),
            ("Deploy Automation", self.deploy_automation()),
            ("Deploy Webhooks", self.deploy_webhooks()),
            ("Configure Webhooks", self.configure_default_webhooks()),
        ]

        results = {}
        for step_name, step_coro in steps:
            try:
                results[step_name] = await step_coro
            except Exception as e:
                console.print(f"❌ Error in {step_name}: {e}", style="red")
                results[step_name] = False

        # Verification
        verification_results = await self.verify_deployment()

        await self.disconnect()

        # Summary
        console.print("\n" + "=" * 60)
        console.print("📋 DEPLOYMENT SUMMARY", style="bold")
        console.print("=" * 60)

        all_steps_passed = all(results.values())
        all_verifications_passed = all(verification_results.values())

        console.print("\nDeployment Steps:")
        for step_name, passed in results.items():
            status = "✅ SUCCESS" if passed else "❌ FAILED"
            style = "green" if passed else "red"
            console.print(f"  {step_name:<25} {status}", style=style)

        console.print("\nVerification Results:")
        for check_name, passed in verification_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            style = "green" if passed else "red"
            console.print(f"  {check_name:<25} {status}", style=style)

        console.print("=" * 60)

        if all_steps_passed and all_verifications_passed:
            console.print("🎉 Deployment completed successfully!", style="bold green")
            console.print("\nNext steps:")
            console.print("1. Deploy Edge Functions to handle webhooks")
            console.print("2. Configure environment variables for external services")
            console.print("3. Test webhook endpoints and scheduled jobs")
            console.print(
                "4. Run 'python scripts/verification/verify_extensions.py' "
                "for detailed verification"
            )
        else:
            console.print(
                "⚠️  Deployment completed with issues. Review output above.",
                style="bold yellow",
            )

        return all_steps_passed and all_verifications_passed

def get_database_url() -> str:
    """Get database URL from environment."""
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        console.print("❌ Database URL not found.", style="red")
        console.print("Set one of these environment variables:")
        console.print("  - SUPABASE_DB_URL")
        console.print("  - DATABASE_URL")
        sys.exit(1)

    return database_url

async def main():
    """Main deployment function."""
    database_url = get_database_url()

    # Get schema path
    script_dir = Path(__file__).parent
    schema_path = script_dir.parent.parent / "supabase" / "schemas"

    if not schema_path.exists():
        console.print(f"❌ Schema directory not found: {schema_path}", style="red")
        sys.exit(1)

    deployer = ExtensionDeployer(database_url, schema_path)
    success = await deployer.full_deployment()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
