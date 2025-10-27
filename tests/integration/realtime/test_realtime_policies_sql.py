"""Lightweight checks for Realtime authorization migration.

These tests do not connect to a database. They ensure our migration file
contains the core constructs for private channel authorization per plan.
"""

from __future__ import annotations

from pathlib import Path


def test_realtime_policy_migration_exists() -> None:
    """Ensure the Realtime policy migration file is present on disk."""
    path = Path("supabase/migrations/20251027_01_realtime_policies.sql")
    assert path.exists(), "Realtime policy migration is missing"


def test_realtime_policy_contains_key_clauses() -> None:
    """Validate essential clauses exist in the migration content.

    This verifies usage of realtime.topic(), authenticated role targeting, and
    both SELECT/INSERT policies for broadcast and presence extensions.
    """
    sql = Path("supabase/migrations/20251027_01_realtime_policies.sql").read_text(
        encoding="utf-8"
    )
    # Core signals we rely on
    assert "realtime.topic()" in sql
    assert 'ON "realtime"."messages"' in sql
    assert "FOR SELECT" in sql
    assert "FOR INSERT" in sql
    assert "TO authenticated" in sql
    # Topic patterns we support
    assert "split_part((SELECT realtime.topic()), ':'" in sql
    assert "= 'user'" in sql
    assert "= 'session'" in sql
    # Extensions covered
    assert "'broadcast'" in sql and "'presence'" in sql
