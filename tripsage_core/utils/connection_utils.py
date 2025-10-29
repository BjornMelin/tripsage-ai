"""Slim database URL parsing helpers and exceptions.

- Parse PostgreSQL URLs safely into structured credentials
- Provide exceptions used by callers
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import ParseResult, quote_plus, unquote_plus, urlparse

from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


class DatabaseURLParsingError(Exception):
    """Raised when database URL parsing fails."""


class DatabaseValidationError(Exception):
    """Raised when database connection validation fails."""


class ConnectionCredentials(BaseModel):
    """Structured database credentials parsed from a URL."""

    scheme: str = Field(..., description="Database scheme (postgresql, postgres)")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    hostname: str = Field(..., description="Database hostname")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database: str = Field(default="postgres", description="Database name")
    query_params: dict[str, str] = Field(
        default_factory=dict, description="Query parameters"
    )

    model_config = {"frozen": True}

    def to_connection_string(self, mask_password: bool = False) -> str:
        """Convert credentials to a connection string."""
        password = "***MASKED***" if mask_password else quote_plus(self.password)
        encoded_username = quote_plus(self.username)
        url = (
            f"{self.scheme}://{encoded_username}:{password}"
            f"@{self.hostname}:{self.port}/{self.database}"
        )
        query_params: dict[str, str] = dict(getattr(self, "query_params", {}))
        if query_params:
            params: list[str] = []
            for k, v in query_params.items():
                params.append(f"{quote_plus(k)}={quote_plus(v)}")
            query_string = "&".join(params)
            url += f"?{query_string}"
        return url

    def sanitized_for_logging(self) -> str:
        """Return masked connection string for logs."""
        return self.to_connection_string(mask_password=True)


class DatabaseURLParser:
    """Secure database URL parser with basic validation."""

    VALID_SCHEMES = frozenset(["postgresql", "postgres"])

    def __init__(self):
        """Create a new parser instance.

        Logger is namespaced to class for clarity in logs.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse_url(self, url: str) -> ConnectionCredentials:
        """Parse database URL into validated credentials.

        Raises DatabaseURLParsingError on invalid input.
        """
        try:
            self._validate_url_security(url)
            parsed = urlparse(url)
            components = self._extract_components(parsed)
            creds = ConnectionCredentials(**components)
            self.logger.debug("Parsed DB URL for host=%s", creds.hostname)
            return creds
        except ValidationError as e:
            msg = f"Invalid database URL components: {e}"
            self.logger.exception(msg)
            raise DatabaseURLParsingError(msg) from e
        except Exception as e:
            msg = f"Failed to parse database URL: {e}"
            self.logger.exception(msg)
            raise DatabaseURLParsingError(msg) from e

    def _validate_url_security(self, url: object) -> None:
        if not isinstance(url, str) or not url:
            raise DatabaseURLParsingError("URL must be a non-empty string")
        if url != url.strip():
            raise DatabaseURLParsingError("URL contains leading/trailing whitespace")
        import re

        if re.search(r"[\x00-\x1f\x7f-\x9f]", url):
            raise DatabaseURLParsingError("URL contains control characters")
        if "://" not in url:
            raise DatabaseURLParsingError("URL must contain '://'")

    def _extract_components(self, parsed: ParseResult) -> dict[str, Any]:
        if not parsed.scheme or parsed.scheme.lower() not in self.VALID_SCHEMES:
            allowed = ", ".join(self.VALID_SCHEMES)
            raise DatabaseURLParsingError(
                f"Invalid scheme '{parsed.scheme}'. Must be one of: {allowed}"
            )
        if not parsed.hostname:
            raise DatabaseURLParsingError("Hostname is required")
        if not parsed.username:
            raise DatabaseURLParsingError("Username is required")
        if not parsed.password:
            raise DatabaseURLParsingError("Password is required")

        database = "postgres"
        if parsed.path and len(parsed.path) > 1:
            database = unquote_plus(parsed.path[1:])

        query_params: dict[str, str] = {}
        if parsed.query:
            for param in parsed.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[unquote_plus(key)] = unquote_plus(value)
                else:
                    query_params[unquote_plus(param)] = ""

        return {
            "scheme": parsed.scheme.lower(),
            "username": unquote_plus(parsed.username),
            "password": unquote_plus(parsed.password),
            "hostname": parsed.hostname,
            "port": parsed.port or 5432,
            "database": database,
            "query_params": query_params,
        }


__all__ = [
    "ConnectionCredentials",
    "DatabaseURLParser",
    "DatabaseURLParsingError",
    "DatabaseValidationError",
]
