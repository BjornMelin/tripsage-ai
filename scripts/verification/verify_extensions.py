#!/usr/bin/env python3
"""Supabase Extensions Verification Script
Verifies that all required extensions are properly installed and configured.
"""

import asyncio
import os
import sys
from datetime import datetime

import asyncpg
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()

# Extension requirements
REQUIRED_EXTENSIONS = {
    "uuid-ossp": "UUID generation functions",
    "vector": "Vector operations for embeddings",
    "pg_cron": "Scheduled job automation",
    "pg_net": "HTTP requests from database",
    "pg_stat_statements": "Query performance monitoring",
    "btree_gist": "Advanced indexing capabilities",
    "pgcrypto": "Encryption functions",
}

AUTOMATION_TABLES = [
    "notifications",
    "system_metrics",
    "webhook_configs",
    "webhook_logs",
]

REALTIME_TABLES = [
    "trips",
    "chat_messages",
    "chat_sessions",
    "trip_collaborators",
    "itinerary_items",
    "chat_tool_calls",
]


class ExtensionVerifier:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection: asyncpg.Connection | None = None

    async def connect(self):
        """Connect to the database."""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            console.print("✅ Connected to database", style="green")
        except Exception as e:
            console.print(f"❌ Failed to connect to database: {e}", style="red")
            sys.exit(1)

    async def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            await self.connection.close()

    async def verify_extensions(self) -> dict[str, bool]:
        """Verify all required extensions are installed."""
        console.print("\n🔍 Checking Extensions...", style="bold blue")

        query = """
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = ANY($1)
        ORDER BY extname
        """

        results = await self.connection.fetch(query, list(REQUIRED_EXTENSIONS.keys()))
        installed = {row["extname"]: row["extversion"] for row in results}

        table = Table(title="Extension Status")
        table.add_column("Extension", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="magenta")
        table.add_column("Version", style="yellow")

        all_good = True
        for ext_name, description in REQUIRED_EXTENSIONS.items():
            if ext_name in installed:
                status = "✅ Installed"
                version = installed[ext_name]
            else:
                status = "❌ Missing"
                version = "N/A"
                all_good = False

            table.add_row(ext_name, description, status, version)

        console.print(table)
        return all_good

    async def verify_automation_tables(self) -> bool:
        """Verify automation tables exist."""
        console.print("\n🔍 Checking Automation Tables...", style="bold blue")

        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = ANY($1)
        """

        results = await self.connection.fetch(query, AUTOMATION_TABLES)
        existing = {row["table_name"] for row in results}

        table = Table(title="Automation Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Purpose", style="white")

        purposes = {
            "notifications": "User notifications and alerts",
            "system_metrics": "Database performance monitoring",
            "webhook_configs": "Webhook endpoint configuration",
            "webhook_logs": "Webhook execution history",
        }

        all_good = True
        for table_name in AUTOMATION_TABLES:
            if table_name in existing:
                status = "✅ Exists"
            else:
                status = "❌ Missing"
                all_good = False

            table.add_row(table_name, status, purposes.get(table_name, "Unknown"))

        console.print(table)
        return all_good

    async def verify_realtime_setup(self) -> bool:
        """Verify Realtime publication is configured."""
        console.print("\n🔍 Checking Realtime Configuration...", style="bold blue")

        # Check if publication exists
        pub_query = (
            "SELECT pubname FROM pg_publication WHERE pubname = 'supabase_realtime'"
        )
        pub_result = await self.connection.fetchval(pub_query)

        if not pub_result:
            console.print("❌ Realtime publication not found", style="red")
            return False

        # Check tables in publication
        tables_query = """
        SELECT schemaname, tablename 
        FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime'
        ORDER BY tablename
        """

        results = await self.connection.fetch(tables_query)
        configured_tables = {row["tablename"] for row in results}

        table = Table(title="Realtime Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Purpose", style="white")

        purposes = {
            "trips": "Trip updates and collaboration",
            "chat_messages": "Live chat functionality",
            "chat_sessions": "Session status updates",
            "trip_collaborators": "Collaboration changes",
            "itinerary_items": "Itinerary modifications",
            "chat_tool_calls": "AI tool execution status",
        }

        all_good = True
        for table_name in REALTIME_TABLES:
            if table_name in configured_tables:
                status = "✅ Configured"
            else:
                status = "❌ Not configured"
                all_good = False

            table.add_row(table_name, status, purposes.get(table_name, "Unknown"))

        console.print(table)
        console.print(f"\nTotal tables in publication: {len(configured_tables)}")
        return all_good

    async def verify_scheduled_jobs(self) -> bool:
        """Verify pg_cron jobs are configured."""
        console.print("\n🔍 Checking Scheduled Jobs...", style="bold blue")

        try:
            query = """
            SELECT jobname, schedule, command, active 
            FROM cron.job 
            ORDER BY jobname
            """

            results = await self.connection.fetch(query)

            if not results:
                console.print("⚠️  No scheduled jobs found", style="yellow")
                return False

            table = Table(title="Scheduled Jobs")
            table.add_column("Job Name", style="cyan")
            table.add_column("Schedule", style="yellow")
            table.add_column("Active", style="magenta")
            table.add_column("Command Preview", style="white")

            for row in results:
                command_preview = (
                    row["command"][:50] + "..."
                    if len(row["command"]) > 50
                    else row["command"]
                )
                status = "✅ Active" if row["active"] else "❌ Inactive"
                table.add_row(row["jobname"], row["schedule"], status, command_preview)

            console.print(table)
            console.print(f"\nTotal jobs configured: {len(results)}")
            return True

        except Exception as e:
            console.print(f"❌ Error checking scheduled jobs: {e}", style="red")
            return False

    async def verify_webhook_configs(self) -> bool:
        """Verify webhook configurations."""
        console.print("\n🔍 Checking Webhook Configurations...", style="bold blue")

        try:
            query = """
            SELECT name, url, is_active, array_length(events, 1) as event_count
            FROM webhook_configs 
            ORDER BY name
            """

            results = await self.connection.fetch(query)

            if not results:
                console.print("⚠️  No webhook configurations found", style="yellow")
                return False

            table = Table(title="Webhook Configurations")
            table.add_column("Name", style="cyan")
            table.add_column("URL", style="white")
            table.add_column("Active", style="magenta")
            table.add_column("Events", style="yellow")

            for row in results:
                url_preview = (
                    row["url"][:40] + "..." if len(row["url"]) > 40 else row["url"]
                )
                status = "✅ Active" if row["is_active"] else "❌ Inactive"
                table.add_row(
                    row["name"], url_preview, status, str(row["event_count"] or 0)
                )

            console.print(table)
            console.print(f"\nTotal webhook configs: {len(results)}")
            return True

        except Exception as e:
            console.print(f"❌ Error checking webhook configs: {e}", style="red")
            return False

    async def test_functions(self) -> bool:
        """Test critical automation functions."""
        console.print("\n🔍 Testing Automation Functions...", style="bold blue")

        functions_to_test = [
            ("verify_extensions()", "Extension verification"),
            ("verify_automation_setup()", "Automation setup verification"),
            ("list_scheduled_jobs()", "Job listing function"),
        ]

        table = Table(title="Function Tests")
        table.add_column("Function", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="magenta")

        all_good = True
        for func_call, description in functions_to_test:
            try:
                await self.connection.fetch(f"SELECT * FROM {func_call}")
                status = "✅ Working"
            except Exception as e:
                status = f"❌ Error: {str(e)[:30]}..."
                all_good = False

            table.add_row(func_call, description, status)

        console.print(table)
        return all_good

    async def run_comprehensive_check(self):
        """Run all verification checks."""
        console.print(
            Panel.fit(
                "[bold blue]TripSage Supabase Extensions Verification[/bold blue]\n"
                f"Timestamp: {datetime.now().isoformat()}",
                title="🚀 Extension Verifier",
            )
        )

        await self.connect()

        checks = [
            ("Extensions", self.verify_extensions()),
            ("Automation Tables", self.verify_automation_tables()),
            ("Realtime Setup", self.verify_realtime_setup()),
            ("Scheduled Jobs", self.verify_scheduled_jobs()),
            ("Webhook Configs", self.verify_webhook_configs()),
            ("Functions", self.test_functions()),
        ]

        results = {}
        for check_name, check_coro in checks:
            try:
                results[check_name] = await check_coro
            except Exception as e:
                console.print(f"❌ Error in {check_name}: {e}", style="red")
                results[check_name] = False

        await self.disconnect()

        # Summary
        console.print("\n" + "=" * 60)
        console.print("📋 VERIFICATION SUMMARY", style="bold")
        console.print("=" * 60)

        all_passed = True
        for check_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            style = "green" if passed else "red"
            console.print(f"{check_name:<20} {status}", style=style)
            if not passed:
                all_passed = False

        console.print("=" * 60)
        if all_passed:
            console.print(
                "🎉 All checks passed! Extensions are properly configured.",
                style="bold green",
            )
        else:
            console.print(
                "⚠️  Some checks failed. Review the output above.", style="bold yellow"
            )

        return all_passed


async def main():
    """Main function."""
    # Get database URL from environment
    database_url = os.getenv("SUPABASE_DB_URL")
    if not database_url:
        # Try alternative environment variable names
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        console.print(
            "❌ No database URL found. Set SUPABASE_DB_URL or DATABASE_URL "
            "environment variable.",
            style="red",
        )
        sys.exit(1)

    verifier = ExtensionVerifier(database_url)
    success = await verifier.run_comprehensive_check()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
