#!/usr/bin/env python3
"""Utilities for deploying Supabase extensions and related automation objects."""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from rich.console import Console
from rich.panel import Panel


console = Console()


class ExtensionDeployer:
    """Deploy or verify Supabase extensions using curated SQL scripts."""

    def __init__(self, database_url: str, schema_path: Path):
        """Initialize a deployer.

        Args:
            database_url: PostgreSQL connection URL.
            schema_path: Directory containing deployment SQL files.
        """
        self.database_url = database_url
        self.schema_path = schema_path
        self.connection: asyncpg.Connection | None = None

    async def connect(self):
        """Open an asyncpg connection."""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            console.print("Connected to database", style="green")
        except (asyncpg.PostgresError, OSError) as exc:
            console.print(f"Failed to connect: {exc}", style="red")
            sys.exit(1)

    def _ensure_connected(self) -> asyncpg.Connection:
        """Ensure database connection is available."""
        if self.connection is None:
            raise RuntimeError(
                "Database connection not established. Call connect() first."
            )
        return self.connection

    async def disconnect(self):
        """Disconnect from database."""
        try:
            connection = self._ensure_connected()
        except RuntimeError:
            return

        try:
            await connection.close()
        except asyncpg.PostgresError as exc:
            console.print(f"Failed to close connection: {exc}", style="yellow")
        finally:
            self.connection = None

    async def execute_sql_file(
        self, file_path: Path, description: str | None = None
    ) -> bool:
        """Execute the statements contained in a SQL file.

        Args:
            file_path: Path to the SQL file.
            description: Optional descriptive label used for console output.

        Returns:
            True when execution completes without fatal errors, False otherwise.
        """
        try:
            sql_content = file_path.read_text(encoding="utf-8")

            console.print(f"Executing: {description or file_path.name}")

            # Split on semicolon but be careful with function definitions
            statements = self._split_sql_statements(sql_content)

            connection = self._ensure_connected()
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        await connection.execute(statement)
                    except asyncpg.PostgresError as exec_error:
                        console.print(
                            f"Warning in statement {i + 1}: {exec_error}",
                            style="yellow",
                        )
                        # Continue with other statements

            console.print(f"Completed: {description or file_path.name}", style="green")
            return True

        except (OSError, asyncpg.PostgresError) as exc:
            console.print(f"Failed to execute {file_path}: {exc}", style="red")
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
        console.print("\nDeploying extensions...", style="bold blue")

        extensions_file = self.schema_path / "00_extensions.sql"
        if not extensions_file.exists():
            console.print(f"Extensions file not found: {extensions_file}", style="red")
            return False

        return await self.execute_sql_file(
            extensions_file, "Core Extensions and Realtime"
        )

    async def deploy_automation(self) -> bool:
        """Deploy automation functions and jobs."""
        console.print("\nDeploying automation routines...", style="bold blue")

        automation_file = self.schema_path / "07_automation.sql"
        if not automation_file.exists():
            console.print(f"Automation file not found: {automation_file}", style="red")
            return False

        return await self.execute_sql_file(
            automation_file, "Scheduled Jobs and Maintenance"
        )

    async def deploy_webhooks(self) -> bool:
        """Deploy webhook functions."""
        console.print("\nDeploying webhook integration...", style="bold blue")

        webhooks_file = self.schema_path / "08_webhooks.sql"
        if not webhooks_file.exists():
            console.print(f"Webhooks file not found: {webhooks_file}", style="red")
            return False

        return await self.execute_sql_file(
            webhooks_file, "Webhook Functions and Triggers"
        )

    async def run_migration(self) -> bool:
        """Run the migration file."""
        console.print("\nRunning migration script...", style="bold blue")

        migration_file = (
            Path(__file__).parent.parent.parent
            / "supabase"
            / "migrations"
            / "20250611_02_enable_automation_extensions.sql"
        )
        if not migration_file.exists():
            console.print(f"Migration file not found: {migration_file}", style="red")
            return False

        return await self.execute_sql_file(
            migration_file, "Automation Extensions Migration"
        )

    async def verify_deployment(self) -> dict[str, bool]:
        """Verify the deployment was successful."""
        console.print("\nVerifying deployment...", style="bold blue")

        checks = {}
        connection = self._ensure_connected()

        # Check extensions
        try:
            extensions_query = """
            SELECT extname FROM pg_extension
            WHERE extname IN ('pg_cron', 'pg_net', 'vector', 'uuid-ossp', 'pgcrypto')
            """
            extensions = await connection.fetch(extensions_query)
            checks["extensions"] = len(extensions) >= 5
            console.print(f"Extensions installed: {len(extensions)}/5")
        except asyncpg.PostgresError as exc:
            checks["extensions"] = False
            console.print(f"Extension check failed: {exc}", style="red")

        # Check automation tables
        try:
            tables_query = """
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN (
                'notifications', 'system_metrics', 'webhook_configs', 'webhook_logs'
            )
            """
            tables = await connection.fetch(tables_query)
            checks["automation_tables"] = len(tables) >= 4
            console.print(f"Automation tables created: {len(tables)}/4")
        except asyncpg.PostgresError as exc:
            checks["automation_tables"] = False
            console.print(f"Automation tables check failed: {exc}", style="red")

        # Check realtime publication
        try:
            realtime_query = """
            SELECT COUNT(*) as table_count FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
            """
            result = await connection.fetchval(realtime_query)
            checks["realtime"] = (result or 0) >= 6
            console.print(f"Realtime tables configured: {result or 0}/6")
        except asyncpg.PostgresError as exc:
            checks["realtime"] = False
            console.print(f"Realtime check failed: {exc}", style="red")

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
            result = await connection.fetchval(functions_query)
            checks["functions"] = (result or 0) >= 3
            console.print(f"Key functions created: {result or 0}/3")
        except asyncpg.PostgresError as exc:
            checks["functions"] = False
            console.print(f"Functions check failed: {exc}", style="red")

        return checks

    async def configure_default_webhooks(self) -> bool:
        """Configure default webhook endpoints."""
        console.print("\nConfiguring default webhook endpoints...", style="bold blue")

        try:
            # Update webhook URLs to use actual Supabase project URL if available
            supabase_url = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")

            update_query = """
            UPDATE webhook_configs
            SET url = REPLACE(url, 'https://your-domain.supabase.co', $1)
            WHERE url LIKE '%your-domain.supabase.co%'
            """

            connection = self._ensure_connected()
            await connection.execute(update_query, supabase_url)
            console.print(f"Updated webhook URLs to use: {supabase_url}")
            return True

        except asyncpg.PostgresError as exc:
            console.print(f"Could not update webhook URLs: {exc}", style="yellow")
            return False

    async def full_deployment(self):
        """Execute the full deployment workflow and report results."""
        console.print(
            Panel.fit(
                "[bold blue]Supabase automation deployment[/bold blue]\n"
                "Applies extension scripts, automation routines, and webhook defaults.",
                title="Deployment Summary",
            )
        )

        await self.connect()

        steps = [
            ("deploy_extensions", self.deploy_extensions()),
            ("run_migration", self.run_migration()),
            ("deploy_automation", self.deploy_automation()),
            ("deploy_webhooks", self.deploy_webhooks()),
            ("configure_webhooks", self.configure_default_webhooks()),
        ]

        step_results: dict[str, bool] = {}
        for step_name, step_coro in steps:
            try:
                step_results[step_name] = await step_coro
            except asyncpg.PostgresError as exc:
                console.print(f"{step_name} failed: {exc}", style="red")
                step_results[step_name] = False

        verification_results = await self.verify_deployment()
        await self.disconnect()

        console.print("\n" + "=" * 60)
        console.print("Deployment summary", style="bold")
        console.print("=" * 60)

        console.print("\nExecution results:")
        for step_name, passed in step_results.items():
            status = "success" if passed else "failed"
            style = "green" if passed else "red"
            console.print(f"  {step_name:<25} {status}", style=style)

        console.print("\nVerification checks:")
        for check_name, passed in verification_results.items():
            status = "pass" if passed else "fail"
            style = "green" if passed else "red"
            console.print(f"  {check_name:<25} {status}", style=style)

        console.print("=" * 60)

        deployment_ok = all(step_results.values())
        verification_ok = all(verification_results.values())

        if deployment_ok and verification_ok:
            console.print(
                "Deployment completed successfully. Proceed with smoke testing.",
                style="bold green",
            )
        else:
            console.print(
                "Deployment completed with issues. Review failed steps above.",
                style="bold yellow",
            )

        return deployment_ok and verification_ok


def get_database_url() -> str:
    """Return the database URL from the environment or exit."""
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        console.print("Database URL not found.", style="red")
        console.print("Set one of these environment variables:")
        console.print("  - SUPABASE_DB_URL")
        console.print("  - DATABASE_URL")
        sys.exit(1)

    return database_url


async def main():
    """Main deployment function."""
    database_url = get_database_url()

    script_dir = Path(__file__).parent
    schema_path = script_dir.parent.parent / "supabase" / "schemas"

    if not schema_path.exists():
        console.print(f"Schema directory not found: {schema_path}", style="red")
        sys.exit(1)

    deployer = ExtensionDeployer(database_url, schema_path)
    success = await deployer.full_deployment()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
