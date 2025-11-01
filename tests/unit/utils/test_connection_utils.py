"""Unit tests for connection utility helpers."""

from __future__ import annotations

import pytest

from tripsage_core.utils.connection_utils import (
    ConnectionCredentials,
    DatabaseURLParser,
    DatabaseURLParsingError,
)


def test_parse_url_produces_structured_credentials() -> None:
    """Parser should return fully populated credentials."""
    parser = DatabaseURLParser()

    creds = parser.parse_url(
        "postgresql://travel_admin:pa%24s@db.example.com:5433/trips_db"
        "?sslmode=require&application_name=tripsage"
    )

    assert creds.username == "travel_admin"
    assert creds.password == "pa$s"
    assert creds.hostname == "db.example.com"
    assert creds.port == 5433
    assert creds.database == "trips_db"
    assert creds.query_params["sslmode"] == "require"
    assert creds.query_params["application_name"] == "tripsage"


def test_sanitized_connection_string_masks_password() -> None:
    """Sanitised connection string must conceal passwords."""
    creds = ConnectionCredentials(
        scheme="postgresql",
        username="agent",
        password="super-secret",
        hostname="localhost",
        port=5432,
        database="agents",
        query_params={"sslmode": "prefer"},
    )

    sanitized = creds.sanitized_for_logging()

    assert "***MASKED***" in sanitized
    assert "super-secret" not in sanitized
    assert sanitized.endswith("sslmode=prefer")


def test_parse_url_rejects_invalid_scheme() -> None:
    """Unsupported schemes should raise parsing errors."""
    parser = DatabaseURLParser()

    with pytest.raises(DatabaseURLParsingError):
        parser.parse_url("mysql://user:pass@localhost:3306/db")


def test_parse_url_requires_password() -> None:
    """Missing credentials should surface as parsing errors."""
    parser = DatabaseURLParser()

    with pytest.raises(DatabaseURLParsingError):
        parser.parse_url("postgresql://user@localhost:5432/db")
