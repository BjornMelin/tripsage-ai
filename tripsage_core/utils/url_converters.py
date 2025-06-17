"""
Database URL conversion utilities for Supabase and PostgreSQL.

This module provides secure conversion between Supabase HTTPS URLs and
PostgreSQL connection strings, leveraging the secure parsing utilities
from connection_utils.py.
"""

import logging
import re
from typing import Dict, Tuple

from tripsage_core.utils.connection_utils import (
    ConnectionCredentials,
    DatabaseURLParser,
    DatabaseURLParsingError,
)

logger = logging.getLogger(__name__)


class DatabaseURLConverter:
    """
    Convert between Supabase HTTPS URLs and PostgreSQL connection strings.

    This converter handles the dual nature of database connections in TripSage,
    providing secure conversion with validation and error handling.
    """

    # Supabase URL patterns (allow optional trailing path)
    SUPABASE_URL_PATTERN = re.compile(
        r"^https://([a-zA-Z0-9\-]+)\.supabase\.(co|com)(?:/.*)?$"
    )

    # Known Supabase regions and their database hosts
    SUPABASE_REGIONS = {
        "supabase.co": "db.supabase.co",
        "supabase.com": "db.supabase.com",
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.url_parser = DatabaseURLParser()

    def is_supabase_url(self, url: str) -> bool:
        """
        Check if URL is a Supabase HTTPS URL.

        Args:
            url: URL to check

        Returns:
            True if URL matches Supabase pattern
        """
        return bool(self.SUPABASE_URL_PATTERN.match(url))

    def is_postgres_url(self, url: str) -> bool:
        """
        Check if URL is a PostgreSQL connection string.

        Args:
            url: URL to check

        Returns:
            True if URL is a PostgreSQL URL
        """
        return url.startswith(("postgresql://", "postgres://"))

    def extract_supabase_project_ref(self, supabase_url: str) -> Tuple[str, str]:
        """
        Extract project reference and domain from Supabase URL.

        Args:
            supabase_url: Supabase HTTPS URL

        Returns:
            Tuple of (project_ref, domain)

        Raises:
            DatabaseURLParsingError: If URL is not a valid Supabase URL
        """
        if not supabase_url:
            raise DatabaseURLParsingError("URL cannot be None or empty")

        match = self.SUPABASE_URL_PATTERN.match(supabase_url)
        if not match:
            raise DatabaseURLParsingError(
                f"Invalid Supabase URL format: {supabase_url}"
            )

        project_ref = match.group(1)
        domain = f"supabase.{match.group(2)}"

        return project_ref, domain

    def supabase_to_postgres(
        self,
        supabase_url: str,
        password: str,
        *,
        use_pooler: bool = False,
        username: str = "postgres",
        database: str = "postgres",
        sslmode: str = "require",
    ) -> str:
        """
        Convert Supabase HTTPS URL to PostgreSQL connection string.

        Args:
            supabase_url: Supabase project URL (https://[ref].supabase.co)
            password: Database password (usually service role key)
            use_pooler: Use connection pooler (port 6543) instead of direct (5432)
            username: Database username (default: postgres)
            database: Database name (default: postgres)
            sslmode: SSL mode (default: require)

        Returns:
            PostgreSQL connection string

        Raises:
            DatabaseURLParsingError: If conversion fails
        """
        try:
            # Extract project reference
            project_ref, domain = self.extract_supabase_project_ref(supabase_url)

            # Determine database host
            db_domain = self.SUPABASE_REGIONS.get(domain)
            if not db_domain:
                # Fallback for unknown domains
                db_domain = domain.replace("supabase.", "db.supabase.")

            # Construct hostname
            hostname = f"{project_ref}.{db_domain}"

            # Determine port
            port = 6543 if use_pooler else 5432

            # Create credentials object
            credentials = ConnectionCredentials(
                scheme="postgresql",
                username=username,
                password=password,
                hostname=hostname,
                port=port,
                database=database,
                query_params={"sslmode": sslmode},
            )

            # Generate connection string
            postgres_url = credentials.to_connection_string()

            self.logger.info(
                "Converted Supabase URL to PostgreSQL",
                extra={
                    "project_ref": project_ref,
                    "use_pooler": use_pooler,
                    "hostname": hostname,
                },
            )

            return postgres_url

        except Exception as e:
            error_msg = f"Failed to convert Supabase URL: {e}"
            self.logger.error(error_msg)
            raise DatabaseURLParsingError(error_msg) from e

    def postgres_to_supabase(
        self, postgres_url: str, *, domain: str = "supabase.co"
    ) -> Tuple[str, str]:
        """
        Extract Supabase project reference from PostgreSQL URL.

        Args:
            postgres_url: PostgreSQL connection string
            domain: Supabase domain (co or com)

        Returns:
            Tuple of (supabase_url, project_ref)

        Raises:
            DatabaseURLParsingError: If extraction fails
        """
        try:
            # Parse PostgreSQL URL
            credentials = self.url_parser.parse_url(postgres_url)

            # Extract project reference from hostname
            # Format: [project-ref].db.supabase.co
            hostname_parts = credentials.hostname.split(".")
            if len(hostname_parts) < 3 or "supabase" not in credentials.hostname:
                raise DatabaseURLParsingError(
                    f"Hostname {credentials.hostname} is not a Supabase database host"
                )

            project_ref = hostname_parts[0]

            # Construct Supabase URL
            supabase_url = f"https://{project_ref}.{domain}"

            self.logger.info(
                "Extracted Supabase info from PostgreSQL URL",
                extra={"project_ref": project_ref, "domain": domain},
            )

            return supabase_url, project_ref

        except Exception as e:
            error_msg = f"Failed to extract Supabase info: {e}"
            self.logger.error(error_msg)
            raise DatabaseURLParsingError(error_msg) from e

    def validate_conversion(self, original_url: str, converted_url: str) -> bool:
        """
        Validate that URL conversion preserved essential information.

        Args:
            original_url: Original URL
            converted_url: Converted URL

        Returns:
            True if conversion is valid
        """
        try:
            if self.is_supabase_url(original_url):
                # Original was Supabase, converted should be PostgreSQL
                if not self.is_postgres_url(converted_url):
                    return False

                # Parse converted URL to ensure it's valid
                credentials = self.url_parser.parse_url(converted_url)

                # Check for Supabase hostname pattern
                return "supabase" in credentials.hostname

            elif self.is_postgres_url(original_url):
                # Original was PostgreSQL, converted should be Supabase
                if not self.is_supabase_url(converted_url):
                    return False

                return True

            else:
                # Unknown URL type
                return False

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False


class DatabaseURLDetector:
    """
    Detect and classify database URLs for appropriate handling.

    This detector helps identify URL types and suggest appropriate
    conversion or parsing strategies.
    """

    def __init__(self):
        self.converter = DatabaseURLConverter()
        self.parser = DatabaseURLParser()

    def detect_url_type(self, url: str) -> Dict[str, any]:
        """
        Detect URL type and provide metadata.

        Args:
            url: URL to analyze

        Returns:
            Dictionary with URL type and metadata
        """
        result = {"url": url, "type": "unknown", "valid": False, "metadata": {}}

        try:
            if self.converter.is_supabase_url(url):
                project_ref, domain = self.converter.extract_supabase_project_ref(url)
                result.update(
                    {
                        "type": "supabase",
                        "valid": True,
                        "metadata": {"project_ref": project_ref, "domain": domain},
                    }
                )

            elif self.converter.is_postgres_url(url):
                credentials = self.parser.parse_url(url)
                result.update(
                    {
                        "type": "postgresql",
                        "valid": True,
                        "metadata": {
                            "hostname": credentials.hostname,
                            "port": credentials.port,
                            "database": credentials.database,
                            "has_ssl": "sslmode" in credentials.query_params,
                            "is_supabase_postgres": "supabase" in credentials.hostname,
                        },
                    }
                )

        except Exception as e:
            result["error"] = str(e)

        return result

    def suggest_handler(self, url: str) -> str:
        """
        Suggest appropriate handler for URL type.

        Args:
            url: URL to analyze

        Returns:
            Suggested handler description
        """
        url_info = self.detect_url_type(url)

        if url_info["type"] == "supabase":
            return (
                "Use Supabase client for API operations or "
                "convert to PostgreSQL URL for direct database access"
            )
        elif url_info["type"] == "postgresql":
            if url_info["metadata"].get("is_supabase_postgres"):
                return (
                    "Use PostgreSQL client for direct database access or "
                    "extract Supabase project info for API operations"
                )
            else:
                return "Use PostgreSQL client for database operations"
        else:
            return "Unknown URL type - manual inspection required"


# Convenience functions
def convert_supabase_to_postgres(supabase_url: str, password: str, **kwargs) -> str:
    """
    Convert Supabase URL to PostgreSQL connection string.

    Args:
        supabase_url: Supabase project URL
        password: Database password
        **kwargs: Additional options for conversion

    Returns:
        PostgreSQL connection string
    """
    converter = DatabaseURLConverter()
    return converter.supabase_to_postgres(supabase_url, password, **kwargs)


def detect_database_url_type(url: str) -> Dict[str, any]:
    """
    Detect and analyze database URL type.

    Args:
        url: URL to analyze

    Returns:
        URL type information and metadata
    """
    detector = DatabaseURLDetector()
    return detector.detect_url_type(url)
