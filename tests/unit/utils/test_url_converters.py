"""Tests for :mod:`tripsage_core.utils.url_converters`."""

from __future__ import annotations

import pytest

from tripsage_core.utils.connection_utils import DatabaseURLParsingError
from tripsage_core.utils.url_converters import DatabaseURLConverter


@pytest.fixture(scope="module")
def converter() -> DatabaseURLConverter:
    """Get a database URL converter."""
    return DatabaseURLConverter()


def test_supabase_to_postgres_generates_expected_url(
    converter: DatabaseURLConverter,
) -> None:
    """Test that the database URL converter generates the expected URL."""
    url = converter.supabase_to_postgres(
        "https://example-project.supabase.co",
        password="service-role-key",
    )

    assert url.startswith("postgresql://postgres:service-role-key@")
    assert "example-project.db.supabase.co" in url
    assert "sslmode=require" in url


def test_supabase_to_postgres_pooler_port(converter: DatabaseURLConverter) -> None:
    """Test that the database URL converter generates expected URL with pooler port."""
    url = converter.supabase_to_postgres(
        "https://chat.supabase.com",
        password="service",
        use_pooler=True,
    )

    assert ":6543/" in url


def test_postgres_to_supabase_roundtrip(converter: DatabaseURLConverter) -> None:
    """Test that the database URL converter generates expected URL with pooler port."""
    supabase_url = "https://edge.supabase.co"
    postgres = converter.supabase_to_postgres(supabase_url, password="service")

    restored_url, project_ref = converter.postgres_to_supabase(postgres)

    assert restored_url == supabase_url
    assert project_ref == "edge"


@pytest.mark.parametrize("invalid_url", ["", "http://example.com", "postgresql://db"])
def test_extract_supabase_project_ref_rejects_invalid_urls(
    converter: DatabaseURLConverter,
    invalid_url: str,
) -> None:
    """Test that the database URL converter rejects invalid URLs."""
    with pytest.raises(DatabaseURLParsingError):
        converter.extract_supabase_project_ref(invalid_url)
