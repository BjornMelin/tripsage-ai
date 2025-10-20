#!/usr/bin/env python3
"""Security configuration validator for TripSage.

This script validates the security configuration before deployment,
ensuring that production environments meet security requirements.
"""

import logging
import sys
from pathlib import Path

from tripsage_core.config import Settings, get_settings, validate_configuration


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class SecurityValidator:
    """Comprehensive security validation for TripSage configuration."""

    def __init__(self):
        self.issues: list[str] = []
        self.warnings: list[str] = []

    def validate_configuration_security(self) -> bool:
        """Run comprehensive security validation.

        Returns:
            True if all security checks pass, False otherwise
        """
        logger.info("🔒 Starting security configuration validation...")

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
            logger.exception("❌ Security validation failed with error")
            self.issues.append(f"Validation error: {e}")
            return False

    def _validate_environment_security(self, settings: Settings) -> None:
        """Validate environment-specific security settings."""
        logger.info("🌍 Validating environment security...")

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

    def _validate_secrets_security(self, settings: Settings) -> None:
        """Validate secret security and strength."""
        logger.info("🔐 Validating secrets security...")

        # Get detailed secret validation
        secret_validation = settings.validate_secrets_security()

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

    def _validate_database_security(self, settings: Settings) -> None:
        """Validate database security configuration."""
        logger.info("🗄️ Validating database security...")

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

    def _validate_api_security(self, settings: Settings) -> None:
        """Validate API security configuration."""
        logger.info("🌐 Validating API security...")

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

    def _validate_production_requirements(self, settings: Settings) -> None:
        """Validate production-specific security requirements."""
        if settings.environment != "production":
            return

        logger.info("🏭 Validating production security requirements...")

        # Required security features for production
        required_features = {
            "enable_security_monitoring": (
                "Security monitoring should be enabled in production"
            ),
            "enable_prometheus_metrics": (
                "Metrics collection should be enabled in production"
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

    def _report_results(self, settings: Settings) -> None:
        """Report validation results."""
        logger.info("📊 Security validation report:")
        logger.info("  Environment: %s", settings.environment)
        logger.info("  Debug mode: %s", settings.debug)
        logger.info("  Log level: %s", settings.log_level)

        # Get overall security report
        security_report = settings.get_security_report()

        if security_report["production_ready"]:
            logger.info("✅ Production security validation passed")
        else:
            logger.warning("⚠️ Production security validation has issues")

        # Report issues
        if self.issues:
            logger.exception("❌ %s security issue(s) found:", len(self.issues))
            for issue in self.issues:
                logger.exception(" - %s", issue)

        # Report warnings
        if self.warnings:
            logger.warning("⚠️ %s security warning(s):", len(self.warnings))
            for warning in self.warnings:
                logger.warning("  - %s", warning)

        if not self.issues and not self.warnings:
            logger.info("✅ No security issues or warnings found")


def generate_secure_config_template() -> str:
    """Generate a secure configuration template."""
    try:
        settings = get_settings()
        template = settings.export_env_template(include_secrets=False)

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
ENABLE_PROMETHEUS_METRICS=true
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
    logger.info("📄 Generating secure configuration template...")
    template = generate_secure_config_template()

    if template:
        template_path = Path(".env.secure.template")
        with open(template_path, "w") as f:
            f.write(template)
        logger.info("✅ Secure configuration template saved to %s", template_path)

    # Exit with appropriate code
    if is_secure:
        logger.info("🎉 Security validation completed successfully!")
        sys.exit(0)
    else:
        logger.exception("💥 Security validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
