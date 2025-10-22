#!/usr/bin/env python3
"""Security configuration validator for TripSage.

Validates configuration using `tripsage_core.config.Settings` when available,
checks common pitfalls, and emits a concise report with proper exit codes.
"""

import logging
import sys
from pathlib import Path
from typing import Any, ClassVar

from tripsage_core.config import get_settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def validate_configuration() -> bool:
    """Basic configuration validation.

    Returns:
        True if `get_settings()` can instantiate settings, else False.
    """
    try:
        _ = get_settings()
        return True
    except (RuntimeError, ImportError, ValueError):
        return False


def validate_secrets_security(settings: Any) -> dict[str, bool]:
    """Validate common secret fields for strength and placeholders.

    Args:
        settings: Settings instance from tripsage_core.

    Returns:
        Mapping of field name to boolean indicating whether it appears secure.
    """
    candidates = [
        "secret_key",
        "database_service_key",
        "database_jwt_secret",
        "openai_api_key",
    ]
    result: dict[str, bool] = {}

    for name in candidates:
        if not hasattr(settings, name):
            continue
        try:
            value = getattr(settings, name)
            # Handle SecretStr-like objects
            if hasattr(value, "get_secret_value"):
                value = value.get_secret_value()
            value = str(value)
            is_secure = len(value) >= 16 and not value.lower().startswith(
                ("test", "demo", "placeholder", "changeme")
            )
            result[name] = is_secure
        except (AttributeError, TypeError, ValueError):
            result[name] = False

    return result


class SecurityValidator:
    """Security validation for TripSage configuration."""

    # Sensitive field names that should not appear in logs
    SENSITIVE_FIELDS: ClassVar[set[str]] = {
        "secret_key",
        "database_service_key",
        "database_jwt_secret",
        "openai_api_key",
        "cors_origins",  # May contain sensitive origin URLs
    }

    def __init__(self):
        """Initialize security configuration validator."""
        self.issues: list[str] = []
        self.warnings: list[str] = []

    def _sanitize_issue_message(self, message: str) -> str:
        """Sanitize issue messages to avoid logging sensitive information.

        Args:
            message: The original issue message.

        Returns:
            Sanitized message with sensitive field names redacted.
        """
        sanitized = message

        # Replace specific sensitive field names with generic terms
        secret_fields = {
            "secret_key",
            "database_service_key",
            "database_jwt_secret",
            "openai_api_key",
        }
        for field in self.SENSITIVE_FIELDS:
            if field in sanitized and field in secret_fields:
                sanitized = sanitized.replace(field, "a secret field")

        # Handle CORS origins separately (they don't follow the same pattern)
        if "CORS origin " in sanitized:
            # Find the position after "CORS origin " and redact everything
            # until the next space or end
            cors_prefix = "CORS origin "
            start_pos = sanitized.find(cors_prefix)
            if start_pos != -1:
                end_pos = sanitized.find(" ", start_pos + len(cors_prefix))
                if end_pos == -1:
                    # No space found, redact to end of string
                    end_pos = len(sanitized)
                sanitized = (
                    sanitized[: start_pos + len(cors_prefix)]
                    + "[REDACTED]"
                    + sanitized[end_pos:]
                )

        return sanitized

    def validate_configuration_security(self) -> bool:
        """Run security validation.

        Returns:
            True if all security checks pass, False otherwise
        """
        logger.info("Starting security configuration validation...")

        try:
            # Load and validate basic configuration
            if not validate_configuration():
                self.issues.append("Basic configuration validation failed")
                return False

            settings = get_settings()

            # Run security checks
            self._validate_environment_security(settings)
            self._validate_secrets_security(settings)
            self._validate_database_security(settings)
            self._validate_api_security(settings)
            self._validate_production_requirements(settings)

            # Report results
            self._report_results(settings)

            return len(self.issues) == 0

        except Exception as e:
            logger.exception("Security validation failed with error")
            self.issues.append(f"Validation error: {e}")
            return False

    def _validate_environment_security(self, settings: Any) -> None:
        """Validate environment-specific security settings."""
        logger.info("Validating environment security...")

        if settings.environment == "production":
            if settings.debug:
                self.issues.append("Debug mode is enabled in production environment")

            if settings.log_level.upper() == "DEBUG":
                self.warnings.append(
                    "Debug logging enabled in production "
                    "(potential information disclosure)"
                )

        elif settings.environment == "development":
            if not settings.debug:
                self.warnings.append(
                    "Debug mode disabled in development (may hinder debugging)"
                )

    def _validate_secrets_security(self, settings: Any) -> None:
        """Validate secret security and strength."""
        logger.info("Validating secrets security...")

        # Get detailed secret validation
        secret_validation = validate_secrets_security(settings)

        for field_name, is_secure in secret_validation.items():
            if not is_secure:
                if settings.environment == "production":
                    self.issues.append(
                        f"Insecure secret detected for {field_name} in production"
                    )
                else:
                    self.warnings.append(
                        f"Weak secret detected for {field_name} "
                        f"(acceptable in {settings.environment})"
                    )

        # Check for fallback patterns in production
        if settings.environment == "production":
            for pattern in settings.FALLBACK_SECRET_PATTERNS:
                for field_name in [
                    "secret_key",
                    "database_service_key",
                    "database_jwt_secret",
                    "openai_api_key",
                ]:
                    secret_value = getattr(settings, field_name).get_secret_value()
                    if secret_value.startswith(pattern):
                        self.issues.append(
                            f"Production secret for {field_name} "
                            f"appears to be a fallback/test value"
                        )

    def _validate_database_security(self, settings: Any) -> None:
        """Validate database security configuration."""
        logger.info("Validating database security...")

        database_url = str(settings.database_url)

        # Check for test/development URLs in production
        if settings.environment == "production":
            if "test" in database_url.lower() or "dev" in database_url.lower():
                self.issues.append(
                    "Production environment using test/development database URL"
                )

            if not database_url.startswith("https://"):
                self.issues.append("Database URL should use HTTPS in production")

        # Check PostgreSQL URL security
        if settings.postgres_url:
            postgres_url = str(settings.postgres_url)
            if "localhost" in postgres_url and settings.environment == "production":
                self.warnings.append("PostgreSQL URL points to localhost in production")

    def _validate_api_security(self, settings: Any) -> None:
        """Validate API security configuration."""
        logger.info("Validating API security...")

        # Validate CORS origins
        for origin in settings.cors_origins:
            if origin == "*" and settings.environment == "production":
                self.issues.append("CORS origins set to wildcard (*) in production")
            elif "localhost" in origin and settings.environment == "production":
                self.warnings.append(
                    f"CORS origin {origin} includes localhost in production"
                )

        # Check credentials setting
        if not settings.cors_credentials and settings.environment == "production":
            self.warnings.append(
                "CORS credentials disabled in production (may break authentication)"
            )

    def _validate_production_requirements(self, settings: Any) -> None:
        """Validate production-specific security requirements."""
        if settings.environment != "production":
            return

        logger.info("Validating production security requirements...")

        # Required security features for production
        required_features = {
            "enable_security_monitoring": (
                "Security monitoring should be enabled in production"
            ),
        }

        for feature, message in required_features.items():
            if hasattr(settings, feature) and not getattr(settings, feature):
                self.warnings.append(message)

        # Validate Redis security
        if settings.redis_url and settings.redis_password is None:
            self.warnings.append(
                "Redis connection without authentication in production"
            )

    def _report_results(self, settings: Any) -> None:
        """Report validation results."""
        logger.info("Security validation report:")
        logger.info("  Environment: %s", settings.environment)
        logger.info("  Debug mode: %s", settings.debug)
        logger.info("  Log level: %s", settings.log_level)

        # Get overall security report (if method exists)
        security_report = {}
        if hasattr(settings, "get_security_report"):
            try:
                security_report = settings.get_security_report()
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning("Failed to get security report from settings: %s", e)

        if security_report.get("production_ready", False):
            logger.info("Production security validation passed")
        else:
            logger.warning("Production security validation has issues")

        # Report issues
        if self.issues:
            logger.exception("%s security issue(s) found:", len(self.issues))
            for issue in self.issues:
                sanitized_issue = self._sanitize_issue_message(issue)
                logger.exception(" - %s", sanitized_issue)

        # Report warnings
        if self.warnings:
            logger.warning("%s security warning(s):", len(self.warnings))
            for warning in self.warnings:
                sanitized_warning = self._sanitize_issue_message(warning)
                logger.warning("  - %s", sanitized_warning)

        if not self.issues and not self.warnings:
            logger.info("No security issues or warnings found")


def generate_secure_config_template() -> str:
    """Generate a secure configuration template."""
    try:
        settings = get_settings()

        # Check if export_env_template method exists
        if hasattr(settings, "export_env_template"):
            try:
                template = settings.export_env_template(include_secrets=False)  # type: ignore[reportAttributeAccessIssue]
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(
                    "Failed to export environment template from settings: %s", e
                )
                template = "# Unable to generate template from settings\n"
        else:
            logger.warning("Settings object does not support template export")
            template = "# Template export not supported by current settings\n"

        # Add security comments
        return f"""# TripSage Secure Configuration Template
# Generated by security validator
#
# SECURITY NOTES:
# - Replace all placeholder values with actual secure values
# - Use strong, unique secrets for each environment
# - Never commit actual secrets to version control
# - Use secret management services in production
# - Validate configuration before deployment

{template}

# Additional Security Settings
# Set these for enhanced security:

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_REQUESTS_PER_HOUR=1000

# Monitoring (recommended for production)
ENABLE_SECURITY_MONITORING=true
ENABLE_DATABASE_MONITORING=true

# Production-specific settings
# Uncomment and configure for production:
# ENVIRONMENT=production
# DEBUG=false
# LOG_LEVEL=INFO
"""

    except Exception:
        logger.exception("Failed to generate secure config template")
        return ""


def main():
    """Main entry point for security validation."""
    validator = SecurityValidator()

    # Run validation
    is_secure = validator.validate_configuration_security()

    # Generate secure template
    logger.info("Generating secure configuration template...")
    template = generate_secure_config_template()

    if template:
        template_path = Path(".env.secure.template")
        with template_path.open("w", encoding="utf-8") as f:
            f.write(template)
        logger.info("Secure configuration template saved to %s", template_path)

    # Exit with appropriate code
    if is_secure:
        logger.info("Security validation completed successfully")
        sys.exit(0)
    else:
        logger.exception("Security validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
